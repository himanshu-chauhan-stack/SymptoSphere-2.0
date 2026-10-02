"""Generate scientific figures from completed JSON reports, never invented metrics."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
EVAL=ROOT/'evaluation'

def load(name):return json.loads((EVAL/name).read_text(encoding='utf-8'))

def main():
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})
    out=EVAL/'figures';out.mkdir(exist_ok=True)
    candidate=load('candidate_report.json');test=load('official_test_report.json');paired=load('paired_validation_interviews.json')
    views=['initial','answers3','answers5','answers7','answers10','unknown_demographics7','retention40','retention80','full']
    fig,ax=plt.subplots(figsize=(12,5.5));x=np.arange(len(views));width=.24
    for j,(metric,color) in enumerate([('top1','#167d80'),('top3','#68adad'),('macro_f1','#355271')]):
        ys=[test['metrics'][v][metric] for v in views]
        ci=np.array([test['metrics'][v]['profile_bootstrap_95ci'][metric] for v in views])
        ax.bar(x+(j-1)*width,ys,width,label=metric.replace('_',' ').title(),color=color)
        ax.errorbar(x+(j-1)*width,ys,yerr=np.vstack([np.maximum(0,np.array(ys)-ci[:,0]),np.maximum(0,ci[:,1]-np.array(ys))]),fmt='none',ecolor='#243942',capsize=2,linewidth=.8)
    ax.set_xticks(x,['Initial','3 answers','5 answers','7 answers','10 answers','7 / demo unknown','40% retained','80% retained','Complete'],rotation=22,ha='right')
    ax.set_ylim(0,1.08);ax.set_ylabel('Synthetic metric (fraction)');ax.set_title(f"Frozen {test['selected_model']} · official test n={test['test_rows_validated']:,}")
    ax.legend(ncol=3,loc='upper left');ax.axvline(5.5,color='#ccc',linestyle='--')
    fig.text(.08,.015,'Complete/retention views include many negative and history answers. 100 profile-group bootstrap replicates. These are not clinical accuracy.',fontsize=9)
    fig.tight_layout(rect=(0,.045,1,1));fig.savefig(out/'official_test_evidence_views.png');plt.close(fig)

    fig,axes=plt.subplots(2,3,figsize=(11,7),sharex=True,sharey=True)
    for ax,view in zip(axes.flat,['initial','answers3','answers5','answers7','answers10','full']):
        ax.plot([0,1],[0,1],'--',color='#aaa',label='Ideal reference')
        for method,color in [('identity','#167d80'),('temperature','#b77740')]:
            bins=candidate['calibration']['check_metrics'][view][method]['reliability_bins']
            ax.plot([b['mean_confidence'] for b in bins],[b['accuracy'] for b in bins],'o-',color=color,label=method,markersize=4)
        ax.set_title(view);ax.set_xlim(0,1);ax.set_ylim(0,1);ax.set_xlabel('Mean top-label score');ax.set_ylabel('Observed synthetic correctness')
    axes[0,0].legend(fontsize=8);fig.suptitle('Independent calibration check · 3,000 profiles/view · sparse gate failed')
    fig.text(.08,.01,'Equal-width 10-bin top-label reliability. Empty bins omitted. UI percentages are withheld; clinical risk is not validated.',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.96));fig.savefig(out/'calibration_reliability.png');plt.close(fig)

    fig,axes=plt.subplots(1,2,figsize=(11,4.8));turns=[1,3,5,7,10]
    for policy,color in [('adaptive','#167d80'),('fixed','#355271'),('random','#b77740')]:
        for ax,metric in zip(axes,['top1','top3']):
            values=[paired['policies'][policy]['turn_metrics'][str(k)][metric] for k in turns]
            ci=np.array([paired['policies'][policy]['turn_metrics'][str(k)]['profile_bootstrap_95ci'][metric] for k in turns])
            ax.plot(turns,values,'o-',label=policy,color=color);ax.fill_between(turns,ci[:,0],ci[:,1],alpha=.10,color=color)
            ax.set_xticks(turns);ax.set_ylim(0,1);ax.set_xlabel('Interview turns (initial complaint + questions/skips)');ax.set_ylabel(metric.title())
    axes[0].legend();fig.suptitle('Paired supplementary final-validation interviews · n=128 · frozen classifier')
    fig.text(.06,.01,'Identical demographics and skip uniforms across policies; 15% simulated skips, 25% independent demographic missingness. No clinical utility claim.',fontsize=8.5)
    fig.tight_layout(rect=(0,.05,1,.94));fig.savefig(out/'paired_validation_questions.png');plt.close(fig)
    print('Generated 3 figures from completed measured reports')

if __name__=='__main__':main()
