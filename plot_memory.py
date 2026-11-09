"""Render the source-derived dynamic shared-memory budgets, separately from performance."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

names=['Routed experts','Histogram bins','Tiled engine']
original=[226.5,128,108]
compact=[81,64,72]
fig,ax=plt.subplots(figsize=(10,5.7),layout='constrained')
fig.set_facecolor('#fafcfe');ax.set_facecolor('#fafcfe')
x=range(3);width=.32
old=ax.bar([v-width/2 for v in x],original,width,label='Original source budget',color='#aebdcd')
new=ax.bar([v+width/2 for v in x],compact,width,label='Compact SM120 budget',color='#187c91')
ax.bar_label(old,fmt='%g KiB',padding=4,fontsize=10)
ax.bar_label(new,fmt='%g KiB',padding=4,fontsize=10)
ax.axhline(99,color='#b14c47',linestyle='--',linewidth=1.5,label='Measured per-block opt-in limit: 99 KiB')
ax.set_xticks(list(x),names);ax.set_ylabel('Dynamic shared memory per block (KiB)');ax.set_ylim(0,260)
ax.set_title('Shared memory that fits RTX 5060 Ti',loc='left',fontsize=17,pad=16)
ax.legend(loc='upper right',frameon=False,fontsize=9)
ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
fig.supxlabel('Requant Network research · Source-derived footprints; exact expert/histogram checks and a complete small-model proof pass.\nTiled-engine value is its configured footprint. These bars are memory budgets, not speedups.',fontsize=9,color='#46566a')
Path('figures').mkdir(exist_ok=True)
fig.savefig('figures/shared-memory.png',dpi=180)
fig.savefig('figures/shared-memory.svg')
svg=Path('figures/shared-memory.svg');svg.write_bytes(svg.read_bytes().replace(b'\r\n',b'\n'))
print('Rendered shared-memory budget comparison')
