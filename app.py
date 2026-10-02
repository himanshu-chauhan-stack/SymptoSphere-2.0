"""Preserved Flask/Jinja application with one stateless evidence service."""
from __future__ import annotations
import json
import os
from pathlib import Path
from flask import Flask,abort,jsonify,render_template,request
from werkzeug.exceptions import HTTPException
from ml.predictor import SymptoPredictor,MODELS
from ml.evidence_schema import EvidenceSchema,EvidenceError,SCHEMA_VERSION,empty_state
from ml.text_extraction import extract_suggestions
from knowledge.safety import safety_check

BASE_DIR=Path(__file__).resolve().parent


def unique_object(pairs):
    obj={}
    for k,v in pairs:
        if k in obj:raise EvidenceError('duplicate_field','body','Duplicate JSON fields are not allowed')
        obj[k]=v
    return obj


def create_app(config=None):
    app=Flask(__name__);app.config.update(MAX_CONTENT_LENGTH=48*1024,MODEL_DIR=MODELS)
    if config:app.config.update(config)
    # No signed sessions, weak fallback secret, patient database or startup training.
    schema=EvidenceSchema();navigation=json.loads((BASE_DIR/'knowledge/navigation.json').read_text(encoding='utf-8'))
    catalogue=schema.catalogue(navigation);by_id={r['id']:r for r in catalogue}
    try:
        service=SymptoPredictor(app.config['MODEL_DIR'],schema);app.config['MODEL_READY']=True
    except (OSError,ValueError,KeyError,TypeError):
        service=None;app.config['MODEL_READY']=False
        app.logger.warning('Required inference artifact unavailable or incompatible')
    app.config['PREDICTOR']=service;app.config['EVIDENCE_SCHEMA']=schema

    @app.context_processor
    def globals_for_views():
        return {'model_ready':service is not None,'model_metadata':service.metadata if service else {},
                'medical_disclaimer':'Educational exploration using synthetic training data. This is not a diagnosis.',
                'regions':navigation['regions']}

    def current_state():
        if request.is_json:
            try:payload=json.loads(request.get_data(cache=False),object_pairs_hook=unique_object)
            except (ValueError,UnicodeDecodeError):abort(400)
        elif request.form.get('state'):
            try:payload=json.loads(request.form['state'],object_pairs_hook=unique_object)
            except (ValueError,UnicodeDecodeError):abort(400)
        else:
            payload=empty_state()
            age=request.form.get('age','').strip()
            if age:
                try:payload['demographics']['age']=int(age)
                except ValueError:raise EvidenceError('invalid_age','age','Use an integer age or leave it unknown')
            payload['demographics']['dataset_sex']=request.form.get('dataset_sex','unknown')
            payload['complaint_scope']=request.form.get('complaint_scope','supported')
            for k in schema.ids:
                e=schema.evidences[k];value=request.form.get('evidence:'+k,'unknown')
                if e['data_type']=='B' and value!='unknown':payload['answers'][k]={'state':value,'values':[],'complete':True}
                elif e['data_type']!='B':
                    vals=[v for v in request.form.getlist('values:'+k) if v!='']
                    if vals:payload['answers'][k]={'state':'known','values':vals,'complete':e['data_type']=='C' or request.form.get('complete:'+k)=='yes'}
            for k in schema.ids:
                if not schema.applicable(k,payload['answers']):payload['answers'].pop(k,None)
            payload['safety_answers']={k[7:]:v for k,v in request.form.items() if k.startswith('safety:')}
            if request.form.getlist('symptoms'):raise EvidenceError('legacy_contract_removed','symptoms','Use canonical Present / Absent / Unknown evidence fields')
        return schema.validate(payload)

    def predict_state(state,explain=True):
        safety=safety_check(state['safety_answers'])
        if safety['urgent']:return {'status':'urgent_help','safety':safety,'ranked_conditions':[],'limitations':[]},200
        if service is None:return {'status':'model_unavailable','safety':safety,'ranked_conditions':[],
                                  'error':{'code':'model_unavailable','message':'The model is unavailable. Your answers are still editable.'}},503
        return service.predict(state,explain=explain),200

    @app.before_request
    def same_origin_posts():
        origin=request.headers.get('Origin')
        # Chromium can send Origin:null for no-referrer HTML form navigation.
        # Only browser-reported same-origin, non-JSON form posts get that exception.
        local_form=(origin=='null' and not request.is_json and request.headers.get('Sec-Fetch-Site')=='same-origin')
        if request.method=='POST' and origin and origin!=request.host_url.rstrip('/') and not local_form:abort(403)

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-src 'self'; font-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'"
        if request.method=='POST' or request.path in ('/predict','/results'):response.headers['Cache-Control']='no-store'
        return response

    @app.get('/')
    def index():return render_template('index.html')

    @app.route('/predict',methods=['GET','POST'])
    def predict():
        initial=current_state() if request.method=='POST' else empty_state()
        return render_template('predict.html',catalogue=catalogue,navigation=navigation,initial_state=initial,by_id=by_id)

    @app.route('/results',methods=['GET','POST'])
    def results():
        if request.method=='GET':return render_template('error.html',error_title='Answers are kept only during your visit',error_message='Start an interview to see possible conditions.'),200
        state=current_state();result,status=predict_state(state)
        return render_template('results.html',result=result,state=state,by_id=by_id),status

    @app.get('/about')
    def about():return render_template('about.html')

    @app.get('/api/health')
    def health():
        return jsonify({'ready':service is not None,'schema_version':SCHEMA_VERSION,
                        'model_version':service.metadata['model_version'] if service else None,
                        'selected_model':service.best_model_name if service else None}),200 if service else 503

    @app.get('/api/evidences')
    def evidences():return jsonify({'schema_version':SCHEMA_VERSION,'evidences':catalogue,'navigation':navigation})

    @app.post('/api/predict')
    def api_predict():
        if not request.is_json:abort(400)
        result,status=predict_state(current_state());return jsonify(result),status

    @app.post('/api/next-question')
    def next_question():
        if not request.is_json:abort(400)
        state=current_state();result,status=predict_state(state,explain=False)
        if status!=200:return jsonify(result),status
        if result['status']!='ok':return jsonify({'status':result['status'],'question':None,'safety':result['safety']})
        return jsonify({'status':'ok','question':result['next_question'],'safety':result['safety']})

    @app.post('/api/extract-symptoms')
    def extract():
        if not request.is_json:abort(400)
        try:data=json.loads(request.get_data(cache=False),object_pairs_hook=unique_object)
        except (ValueError,UnicodeDecodeError):abort(400)
        if not isinstance(data,dict) or set(data)!={'text'}:raise EvidenceError('invalid_text','body','Expected only a text field')
        return jsonify(extract_suggestions(data['text'],schema))

    @app.get('/api/translations/<language>')
    def translations(language):
        if language not in ('en','hi'):abort(404)
        return jsonify(json.loads((BASE_DIR/'translations'/f'{language}.json').read_text(encoding='utf-8-sig')))

    @app.errorhandler(EvidenceError)
    def evidence_error(error):
        response={'error':{'code':error.code,'field':error.field,'message':str(error)}}
        if request.path.startswith('/api/'):return jsonify(response),422
        return render_template('error.html',error_title='Please review your answers',error_message=str(error)),422

    @app.errorhandler(Exception)
    def error(error):
        status=error.code if isinstance(error,HTTPException) else 500
        code={400:'bad_json',403:'origin_rejected',404:'not_found',405:'method_not_allowed',413:'payload_too_large'}.get(status,'internal_error')
        if status==500:app.logger.error('Request failed: %s',type(error).__name__)
        if request.path.startswith('/api/'):return jsonify({'error':{'code':code,'message':'Request could not be processed. Review the input or try again.'}}),status
        return render_template('error.html',error_title='Request could not be processed',error_message='Please review your input or try again.'),status

    return app


app=create_app()
if __name__=='__main__':app.run(host='127.0.0.1',port=int(os.getenv('PORT','5000')),debug=False)
