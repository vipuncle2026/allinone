import {AS_OF,WINDOW,PRODUCTS,SOURCES} from './data.mjs';
import {DEFAULTS,DIMENSIONS,normaliseWeights,rank,repoEstimate} from './engine.mjs';
const $=id=>document.getElementById(id);
let state={...DEFAULTS,weights:[...DEFAULTS.weights]},currentResults=[],currentView='rank';
const escapeHtml=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=v=>Number(v).toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2});
const pct=(v,d=3)=>v===null||v===undefined?'—':Number(v).toFixed(d).replace(/0+$/,'').replace(/\.$/,'')+'%';
const yuan=v=>v>=10000?(v/10000).toLocaleString('zh-CN',{maximumFractionDigits:2})+'万元':v.toLocaleString('zh-CN',{maximumFractionDigits:2})+'元';
const sourcesFor=ids=>(ids||[]).map(id=>SOURCES.find(s=>s.id===id)).filter(Boolean);
const chips=p=>`<div class="source-chips">${sourcesFor(p.source).map(s=>`<button data-source="${s.id}">${escapeHtml(s.org.split(' · ')[0])} · ${escapeHtml(s.type)} ↗</button>`).join('')}</div>`;
const statusName={eligible:'符合硬约束',pending:'待确认',excluded:'不适用'};

function showToast(message){$('toast').textContent=message;$('toast').hidden=false;clearTimeout(showToast.timer);showToast.timer=setTimeout(()=>$('toast').hidden=true,4000);}
function setView(view){currentView=view;document.querySelectorAll('.view').forEach(p=>p.hidden=p.id!==`view-${view}`);document.querySelectorAll('.nav').forEach(n=>{n.classList.toggle('active',n.dataset.view===view);if(n.dataset.view===view)n.setAttribute('aria-current','page');else n.removeAttribute('aria-current');});if(view==='universe')renderUniverse();document.querySelector('.main-content').scrollIntoView({behavior:'smooth',block:'start'});}
function openSource(id){let s=SOURCES.find(x=>x.id===id);if(!s)return;$('source-dialog-content').innerHTML=`<div class="section-label">${escapeHtml(s.type)} · 查阅 ${AS_OF}</div><h3>${escapeHtml(s.title)}</h3><p>${escapeHtml(s.org)}<br>资料原日期：${escapeHtml(s.date)}</p><p>${escapeHtml(s.note)}</p><a href="${s.url}" target="_blank" rel="noopener noreferrer">打开原始资料 ↗</a>`;$('source-dialog').showModal();}
function detailsRow(p,index,conditional=false){
 const showRate=Number.isFinite(p.rateEffective)?pct(p.rateEffective):'—';
 const earningTerm=p.kind==='structured'?'保底现金流与到账后活期暂估（税前）':p.kind==='savings'?'票面年利率 / 按年付息':['fixed','cd'].includes(p.kind)&&state.days>=p.term?`首个存期挂牌${pct(p.rate)}，剩余计划期按活期暂估`:'当前持有/支取情景年化';
 const interestLabel=`按共同计划期${state.days}天情景测算`;
 return `<details class="product-row" data-product="${p.id}"><summary><span class="rank-index">${String(index+1).padStart(2,'0')}</span><div><div class="product-name">${escapeHtml(p.name)}<span class="product-tag">${escapeHtml(p.tag)}</span></div><div class="product-sub">${escapeHtml(p.issuer)} · ${p.min?yuan(p.min)+'起':'门槛需按产品确认'}${p.capacity<state.amount?' · 仅覆盖部分资金':''}</div>${conditional?`<div class="pending-note">待确认 · 不属于今日可购主榜</div>`:''}</div><div class="product-rate"><strong>${showRate}</strong><small>${p.kind==='savings'?'票面年利率':'计划期情景年化'}</small></div><div class="product-score"><b>${p.score.toFixed(1)}</b><small>${conditional?'条件分 / 100':'适配分 / 100'}</small></div><span class="chevron">＋</span></summary><div class="product-detail"><p class="detail-description">${escapeHtml(p.description)}</p><div class="detail-grid"><div class="detail-field"><strong>收益口径</strong>${earningTerm}${p.kind==='structured'?`<br>原保底${pct(p.rate)}，目录/合同条件收益参考${pct(p.upper)}；评分不使用上限`:''}<br>${interestLabel}：${p.interest===null?'未核算，须按具体现金流验证':money(p.interest)+'元（未计适用个人税费）'}</div><div class="detail-field"><strong>本金退出</strong>${escapeHtml(p.exit)}</div><div class="detail-field"><strong>本次可核价且满足保障边界的本金</strong>${money(p.capacity)}元 / ${money(state.amount)}元<br>本行已有本息 ${money(p.bankExisting)}元，不含尚未核验其他银行</div><div class="detail-field"><strong>尚待另行核验与安排的资金</strong>${money(Math.max(0,state.amount-p.capacity))}元<br>不能将同一银行不同网点、卡号当作不同保障主体</div></div><div class="breakdown">${DIMENSIONS.map(([key,name],i)=>`<div><div class="breakdown-label">${name}<b>${p.dimensions[key].toFixed(1)}</b></div><div class="mini-bar"><i style="width:${p.dimensions[key]}%"></i></div><small>权重${p.weights[i].toFixed(1)}% · 贡献${(p.dimensions[key]*p.weights[i]/100).toFixed(1)}</small></div>`).join('')}</div>${p.pending.length?`<p class="pending-note">待确认：${p.pending.map(escapeHtml).join('；')}</p>`:''}<ul class="warning-list">${p.warnings.map(x=>`<li>${escapeHtml(x)}</li>`).join('')}</ul>${chips(p)}</div></details>`;
}
function render(){
 const raw=Number($('amount').value);state.amount=Number.isFinite(raw)?Math.min(1e9,Math.max(0,raw)):0;
 state.days=Math.min(10000,Math.max(1,Number($('days').value)||1));state.existing=Math.min(1e9,Math.max(0,Number($('existing').value)||0));
 state.existingCib=Math.min(1e9,Math.max(0,Number($('existingCib').value)||0));state.exit=$('exit').value;state.province=$('province').value;
 for(const k of ['securities','early','online','split'])state[k]=$(k).checked;
 $('amount-cn').textContent=yuan(state.amount);
 currentResults=rank(PRODUCTS,state);
 const byRate=$('sort').value==='rate';const sorting=a=>byRate?[...a].sort((a,b)=>(b.rateEffective-a.rateEffective)||(b.score-a.score)):a;
 const valid=sorting(currentResults.filter(p=>p.status==='eligible'));
 const pending=sorting(currentResults.filter(p=>p.status==='pending'&&p.score!==null));
 const unscored=currentResults.filter(p=>p.status==='pending'&&p.score===null);
 const excluded=currentResults.filter(p=>p.status==='excluded');
 $('eligible-count').textContent=valid.length;$('pending-count').textContent=pending.length+unscored.length;$('excluded-count').textContent=excluded.length;
 const best=valid[0];
 if(best){
  const rateLabel=best.kind==='structured'?'按共同计划期折算的保底情景年化':best.kind==='savings'?'票面年利率 / 按年付息 / 须到期':['fixed','cd'].includes(best.kind)&&state.days>=best.term?'首个到期利率与余期活期暂估的计划期年化':'本次计划期 / 支取情景的年化利率';
  const runner=valid[1];const noYieldGap=runner&&Math.abs(best.rateEffective-runner.rateEffective)<1e-9;
  $('result-summary').innerHTML=`<div class="recommendation"><div class="recommend-top"><div class="recommend-tag"><span></span>${byRate?'可比年化优先 · 非综合最优':'当前模型综合首位'}</div><div class="context">${yuan(state.amount)} / ${state.days}天计划 / 严格本金边界</div></div><div class="recommend-body"><div><h3>${escapeHtml(best.name)}</h3><p>${noYieldGap?'与下一项比较口径收益相同，差别主要在操作便利和退出灵活性。':byRate?'收益排序不能替代到期、通知与本金退出条件。':'这是权重下的适配首位，不是全国最高利率承诺。'} ${best.kind==='notice'?'只有按约通知支取才能保留通知利率。':''}</p></div><div class="recommend-rate"><strong>${pct(best.rateEffective).replace('%','')}<small>%</small></strong><span>${rateLabel}</span></div></div><div class="recommend-foot"><span>适配分<b>${best.score.toFixed(1)} / 100</b></span><span>本行可核价本金<b>¥${money(best.capacity)}</b></span><span>${best.interest===null?'收益按具体现金流另核':`情景收益<b>¥${money(best.interest)}</b>`}</span></div><div class="recommend-notice">${best.capacity<state.amount?`仍有${money(state.amount-best.capacity)}元未安排。其他银行须独立核价，不能照搬本行利率。`:'此分数不是收益保证或违约概率。仅在正常账户和业务规则下比较；应急资金需另外检查转账限额。'}${['fixed','cd'].includes(best.kind)?' 提前支取部分按活期，无法同时保留所示定期收益。':''}</div></div><div class="stats-strip"><div><strong>${valid.length}</strong>项通过<small>主榜有报价且满足当前筛选</small></div><div><strong>${pending.length+unscored.length}</strong>项待确认<small>${pending.length}项条件分 / ${unscored.length}项不评分</small></div><div><strong>${excluded.length}</strong>项排除<small>不让收益补偿本金与时间硬约束</small></div></div>`;
 }else{
  $('result-summary').innerHTML=`<div class="empty"><strong>当前条件下，没有已核验的合格报价。</strong>${state.amount<=0?'请输入大于0的现金金额。':!state.split&&state.amount>490000?'单家银行全额放置可能超出本息50万元边界。可降低单行金额或允许分散，但仍需逐家核价。':state.existing>=500000?'已填入银行的保障额度可能已用完。请查看另一家银行是否仍有额度，或另选不同投保法人核价，不能通过再开一张卡增加额度。':'请查看待确认项和逐项排除原因。不要为了生成一个榜首而放宽本金约束。'}</div>`;
 }
 $('eligible-list').innerHTML=valid.length?valid.slice(0,5).map((p,i)=>detailsRow(p,i)).join('')+(valid.length>5?`<details class="excluded-more"><summary>展开其余 ${valid.length-5} 项合格方案 ＋</summary>${valid.slice(5).map((p,i)=>detailsRow(p,i+5)).join('')}</details>`:''):'<p class="list-explainer">暂无符合全部条件的已核验样本。</p>';
 $('pending-list').innerHTML=pending.length?pending.map((p,i)=>detailsRow(p,i,true)).join(''):'<p class="list-explainer">当前没有可计算条件分的待确认报价。其他未知条款见产品全景。</p>';
 if(unscored.length)$('pending-list').innerHTML+=`<details class="excluded-more"><summary>另有 ${unscored.length} 项缺少可比现金流 / 报价，不评分 ＋</summary><div class="compact-list">${unscored.map(p=>`<div class="compact-item"><div><strong>${escapeHtml(p.name)}</strong><p>${p.pending.map(escapeHtml).join('；')}${p.observed?' · '+escapeHtml(p.observed)+'（'+escapeHtml(p.observedLabel)+'）':''}</p>${chips(p)}</div><span>N/A</span></div>`).join('')}</div></details>`;
 const compact=p=>`<div class="compact-item"><div><strong>${escapeHtml(p.name)}</strong><p>${p.reasons.map(escapeHtml).join('；')}</p></div><span>N/A</span></div>`;
 const first=excluded.slice(0,5),rest=excluded.slice(5);
 $('excluded-list').innerHTML=`<div class="compact-list">${first.map(compact).join('')}</div>${rest.length?`<details class="excluded-more"><summary>展开其余 ${rest.length} 项排除原因 ＋</summary><div class="compact-list">${rest.map(compact).join('')}</div></details>`:''}`;
 const hasSecurities=state.securities?'有证券账户不改变产品的本金保障性质。':'不开户也能使用存款及部分储蓄国债；开证券账户不会让基金变成保本。';
 const weightTests=[[85,5,3,2,5],[20,30,35,5,10]].map(w=>rank(PRODUCTS,{...state,weights:w}).filter(p=>p.status==='eligible')[0]?.id).filter(Boolean);
 const sensitive=best&&weightTests.some(id=>id!==best.id);
 $('decision-notes').innerHTML=`<div class="decision-note"><strong>${sensitive?'排名对偏好敏感：切换权重可能更换首位。':'不是只有收益率需要比较。'}</strong>${hasSecurities} ${state.exit==='t0'?'你要求当天可取：通知产品未预约退出按活期比较，封闭结构性存款被排除。':state.exit==='t1'?'T+1按工作日口径理解，周末和节假日不能直接当自然次日。':'你允许阶段性锁定，但仍要给募集和到账留出缓冲。'} 当前具体存款报价覆盖中行与兴业样本，不称“全市场最优”；其他银行仍需独立核价。</div>`;
 updateWeightLabels();if(currentView==='universe')renderUniverse();renderRepo();
}
function renderUniverse(){
 let search=$('search').value.trim().toLowerCase(),category=$('category').value;
 let list=currentResults.filter(p=>(category==='all'||p.group===category)&&(!search||(p.name+p.description+p.tag).toLowerCase().includes(search)));
 $('universe-count').textContent=`${PRODUCTS.length} 个样本 / 家族 · 回购覆盖9期限`;
 $('universe-list').innerHTML=list.length?list.map(p=>`<article class="universe-item"><div><h3>${escapeHtml(p.name)}<span class="status-badge ${p.status}">${p.kind==='strategy'?'配置方法':statusName[p.status]}</span></h3><p>${escapeHtml(p.description)}</p><p class="reasons">${p.reasons.length?p.reasons.map(escapeHtml).join('；'):p.pending.length?p.pending.map(escapeHtml).join('；'):'当前满足所选边界，仍需交易前确认账户、实际执行价与限额。'}</p>${chips(p)}</div><div class="universe-observed">${p.observed?escapeHtml(p.observed):p.score!==null?pct(p.rateEffective):'—'}<small>${escapeHtml(p.observedLabel||(p.score!==null?`${p.status==='excluded'?'排除项理论口径，不可据此买入':'可比年化'} · ${p.status==='eligible'?'适配分':p.status==='pending'?'条件分':'总分N/A'}${p.status==='excluded'?'':p.score.toFixed(1)}`:'无可核验统一报价 / 不评分'))}</small></div></article>`).join(''):'<div class="empty">没有匹配的产品。试试其他关键词或类别。</div>';
}
function renderRepo(){
 const a=state.amount,rate=Number($('repo-rate').value),d=Number($('repo-interest').value),occupied=Number($('repo-occupied').value),f=Number($('repo-fee').value);
 if(!(a>0)||!Number.isFinite(rate)||rate<0||!(d>=1)||!Number.isFinite(f)||f<0||occupied<d){$('repo-result').textContent='请输入有效非负费率、至少1天计息天数，且银行卡可用天数不能小于计息天数。';return;}
 const r=repoEstimate({amount:a,rate,interestDays:d,occupiedDays:occupied,feePer100k:f});
 $('repo-result').innerHTML=`<div>以当前 ${yuan(a)} 为例<br><small>毛息 ${money(r.gross)}元 − 佣金 ${money(r.fee)}元 = 净情景收益</small></div><strong>¥ ${money(r.net)}</strong><div>占款期折年化 ${pct(r.annual)}<br><small>覆盖佣金所需名义年化 ≥ ${pct(r.breakEven)}</small></div>`;
}
function updateWeightLabels(){const w=normaliseWeights(state.weights);DIMENSIONS.forEach(([,name],i)=>{$(`weight-label-${i}`).textContent=`${w[i].toFixed(1)}%`;});}
function initialise(){
 $('weights').innerHTML=DIMENSIONS.map(([,name,v],i)=>`<div class="weight-control"><label class="weight-label" for="weight-${i}">${name}<b id="weight-label-${i}">${v}%</b></label><input id="weight-${i}" type="range" min="0" max="100" value="${v}" data-weight="${i}" aria-label="${name}原始权重"></div>`).join('');
 $('source-list').innerHTML=SOURCES.map((s,i)=>`<article class="source-entry" id="source-${s.id}"><div class="source-entry-top"><div><div class="source-id">${String(i+1).padStart(2,'0')} / ${escapeHtml(s.type)}</div><h3>${escapeHtml(s.title)}</h3></div><a class="source-link" href="${s.url}" target="_blank" rel="noopener noreferrer">查看原文 ↗</a></div><div class="source-meta">${escapeHtml(s.org)} · 原日期 ${escapeHtml(s.date)} · 本次查阅 ${AS_OF}</div><p>${escapeHtml(s.note)}</p></article>`).join('');
 const rubric=[['收益效率','45%','得分 = min(100, max(0, 可比年化百分数 ÷ 2 × 100))。活期/通知/定活为当前挂牌情景；定期按是否存满，余期以活期暂估；结构性只按保底现金流和到账后活期暂估，在同一计划期内单利年化；储蓄国债仅展示票面年利率，现金流未完整核验前不评分。'],['退出灵活','25%','活期100；定活两便90；按约1天通知85、7天通知65；临时未通知按活期情景65；允许损息的定期55；不允许损息的到期定期为70−40×期限天数÷1827，最低10；封闭结构性存款与持有到期储蓄国债10。'],['操作便利','15%','活期100；定活两便90（兴业仅柜面取款，便利分50）；整存整取90（中行要求全程手机时权限待确认；兴业官网明确支持定活互转手机渠道）；1天通知80；7天通知75；大额存单80（库存待确认）；163天结构性70、湖北区域65；储蓄国债电子式75。资格和频繁预约带来成本，分值为模型判断。'],['资金覆盖','5%','得分 = 已核价且满足保障边界的本次本金 ÷ 用户输入现金 × 100。未核验其他银行不虚构成全额配置；储蓄国债按本期单账户50万元上限评估。'],['证据质量','10%','完整官方挂牌/说明书/规则100；本周查到但未核验当前额度的7月大额存单公告60。其他未经核验报价不评分。本周读取的兴业同域数据文件按官方来源100计；证据分高不表示收益高或没有信用风险。']];
 $('rubric').innerHTML=rubric.map(([name,w,t])=>`<div class="rubric-row"><strong>${name}<b>${w}</b></strong><span>${t}</span></div>`).join('');
 ['amount','days','existing','existingCib','exit','province','securities','early','online','split','sort'].forEach(id=>$(id).addEventListener(['exit','province','sort'].includes(id)?'change':'input',render));
 ['search','category'].forEach(id=>$(id).addEventListener(id==='category'?'change':'input',renderUniverse));
 ['repo-rate','repo-interest','repo-occupied','repo-fee'].forEach(id=>$(id).addEventListener('input',renderRepo));
 document.addEventListener('click',e=>{
  const view=e.target.closest('[data-view]');if(view){setView(view.dataset.view);return;}
  const src=e.target.closest('[data-source]');if(src){openSource(src.dataset.source);return;}
  const amount=e.target.closest('[data-amount]');if(amount){$('amount').value=amount.dataset.amount;render();return;}
  const preset=e.target.closest('[data-preset]');if(preset){const presets={balanced:[45,25,15,5,10],yield:[85,5,3,2,5],easy:[20,30,35,5,10]};state.weights=presets[preset.dataset.preset];state.weights.forEach((w,i)=>$(`weight-${i}`).value=w);document.querySelectorAll('[data-preset]').forEach(el=>el.classList.toggle('selected',el===preset));render();}
 });
 $('exit').addEventListener('change',()=>{const v=$('exit').value;if(!['t0','t1'].includes(v)){$('days').value=v;render();}});
 $('weights').addEventListener('input',e=>{if(e.target.dataset.weight!==undefined){state.weights[Number(e.target.dataset.weight)]=Number(e.target.value);document.querySelectorAll('[data-preset]').forEach(el=>el.classList.remove('selected'));render();}});
 $('close-dialog').addEventListener('click',()=>$('source-dialog').close());
 $('source-dialog').addEventListener('click',e=>{if(e.target===$('source-dialog')){const b=e.target.getBoundingClientRect();if(e.clientX<b.left||e.clientX>b.right||e.clientY<b.top||e.clientY>b.bottom)e.target.close();}});
 $('share').addEventListener('click',async()=>{if(location.protocol==='file:'){showToast('离线文件没有公网链接。请直接发送HTML文件；对方可在浏览器打开。');return;}const url=new URL(location.href);url.search='';url.hash='';try{await navigator.clipboard.writeText(url.href);showToast(/localhost|127\.0\.0\.1/.test(url.hostname)?'已复制本机预览地址；他人无法访问。对外分享请部署静态网页或发送离线HTML。':'已复制工具链接，不含你的金额与选择。');}catch{showToast('复制受限，请复制浏览器地址；不要附上个人金额。');}});
 $('download-research').addEventListener('click',e=>{e.preventDefault();const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([RESEARCH_NOTE],{type:'text/markdown;charset=utf-8'}));a.download='存放-研究笔记-2026-11-16.md';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);});
 $('export').addEventListener('click',()=>{const result={researchDate:AS_OF,window:WINDOW,warning:'研究快照非实时报价；替代方案并非组合；金额数据仅下载到本地。',profile:state,results:currentResults.map(p=>({id:p.id,name:p.name,status:p.status,score:p.status==='excluded'?null:p.score,rateEffective:p.rateEffective,quotedRate:p.rate??null,capacity:p.capacity,interest:p.interest,dimensions:p.dimensions,normalisedWeights:p.weights,reasons:p.reasons,pending:p.pending,warnings:p.warnings,sources:sourcesFor(p.source).map(s=>({url:s.url,date:s.date,checked:AS_OF}))}))};const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));a.download=`存放-个人筛选结果-${AS_OF}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);showToast('结果已导出到本地，包含你的金额；转发前注意隐私。');});
 const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
 if(today>AS_OF){$('stale').hidden=false;const overdue=Date.parse(today)>Date.parse(AS_OF)+7*86400000;$('stale').textContent=`这是一份${AS_OF}的静态研究快照，${overdue?'已超7天':'已不是研究当日'}。本页仍按研究日筛选，认购窗口和报价可能失效；请先重新核验，当前排名不是今天的购买建议。`;}
 render();
}
initialise();
