import {AS_OF} from './data.mjs';
export const DIMENSIONS = [
  ['returns','收益效率',45],['liquidity','退出灵活',25],['ease','操作便利',15],['coverage','资金覆盖',5],['evidence','证据质量',10]
];
export const DEFAULTS = {amount:100000,securities:false,exit:'t0',days:30,province:'其他',early:true,online:true,split:true,existing:0,existingCib:0,weights:[45,25,15,5,10]};
export const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
export function dayDiff(a,b){return Math.round((Date.parse(b+'T00:00:00Z')-Date.parse(a+'T00:00:00Z'))/86400000);}
export function termDays(months){let d=new Date(AS_OF+'T00:00:00Z');d.setUTCMonth(d.getUTCMonth()+months);return dayDiff(AS_OF,d.toISOString().slice(0,10));}
export function nextWeekday(date){let d=new Date(date+'T00:00:00Z');do{d.setUTCDate(d.getUTCDate()+1);}while([0,6].includes(d.getUTCDay()));return d.toISOString().slice(0,10);}
export function normaliseWeights(weights){let ws=weights.map(x=>clamp(Number(x)||0,0,100));let sum=ws.reduce((a,b)=>a+b,0);return sum?ws.map(x=>x/sum*100):DIMENSIONS.map(x=>x[2]);}
export function evaluate(p,s){
  let reasons=[],pending=[],warnings=[];
  let rate=p.rate,days=s.days,term=p.months?termDays(p.months):p.termDays||0;
  let hold=term||days,locked=0,liquidity=100,ease=p.ease??0,evidence=p.evidence??0;
  const maxLock=s.exit==='t0'?0:s.exit==='t1'?1:Number(s.exit);
  if(!(s.amount>0))reasons.push('请先输入大于0的存款金额');
  if(p.risk==='market')reasons.push('没有满足本工具要求的本金保障；低风险不等于保本');
  if(p.risk==='unknown')pending.push('未取得完整可比的产品合同、可购报价或适用渠道；不编造总分');
  if(p.securities&&!s.securities)reasons.push('需要证券账户');
  if(s.amount<(p.min||0))reasons.push(`未达到${p.min.toLocaleString('zh-CN')}元起购门槛`);
  if(p.available==='closed'||p.saleEnd&&p.saleEnd<AS_OF)reasons.push('研究基准日已结束认购，不能新买入');
  if(p.province&&p.province!==s.province)reasons.push(`仅${p.province}区域销售，请按真实资格选择`);
  if(p.notProvince===s.province)reasons.push(`${s.province}地区不在销售范围`);
  if(p.available==='pending')pending.push('历史公告或特邀可购权限、当日额度尚未核验');
  if(s.online&&p.requiresCounter)reasons.push('官网仅列柜台取款，不符合必须全程手机操作');
  if(p.kind==='notice'){
    const keeps=s.early||p.notice<=maxLock;
    if(!keeps)reasons.push(`保留通知利率需提前${p.notice}天通知，不满足退出约束`);
    rate=days>=p.notice&&p.notice<=maxLock?p.rate:0.05;
    liquidity=rate===0.05?65:p.notice===1?85:65;
    if(rate===0.05)warnings.push('当前按无预约/短持有的活期利率计分，而非通知挂牌利率');
    else warnings.push('需按时预约且按约定支取；未来支取日挂牌可能调整');
  }
  if(p.kind==='flex'){
    const fr=p.flexRates||[.65,.85,.95];
    rate=days>=termDays(12)?fr[2]*0.6:days>=termDays(6)?fr[1]*0.6:days>=termDays(3)?fr[0]*0.6:0.05;
    liquidity=90;warnings.push('按整笔支取评估；按支取日挂牌利率，未来收益非锁定');
  }
  if(['fixed','cd'].includes(p.kind)){
    if(!s.early&&term>maxLock)reasons.push('不接受损失利息，且存满本档期限超过最长锁定时间');
    // Compare one common planned horizon. Do not pretend the first term's rate
    // can be rolled forward: after its maturity assume idle demand at 0.05%.
    rate=days>=term?(p.rate*term+0.05*(days-term))/days:0.05;
    liquidity=s.early?55:Math.max(10,70-40*term/1827);
    if(days<term)warnings.push('计划持有不足本档期限，只按活期计分');
    else warnings.push('按存满期限的条件利率评分；临时提前取出部分仅按活期计息');
    if(p.kind==='fixed'&&s.online&&!p.onlineVerified)pending.push('所用电子存款的手机银行开户及提前支取权限需确认；官网规则页未给出全场景线上保证');
    if(days>term)warnings.push('计划期长于首个存期：余下天数按当前活期0.05%暂估，不假定能以原定期利率续存；未来活期价仍可变');
  }
  if(p.kind==='structured'){
    if(p.maturity){
      locked=dayDiff(AS_OF,nextWeekday(p.maturity));
      // Use the upper-bound disclosed one-business-day settlement, not the nominal term.
      hold=locked;rate=days>=locked?(p.rate*p.termDays+0.05*(days-locked))/days:p.rate*p.termDays/locked;
    }else{locked=term+4;hold=locked;rate=null;}
    liquidity=10;
    if(locked>maxLock)reasons.push(`本金锁定约${locked}天（含募集与到账缓冲），不能提前赎回`);
    if(days<locked)reasons.push(`计划${days}天后用钱，早于可用资金日`);
    warnings.push('只用保底现金流；募集至到账期间未计额外活期利息，到账后至计划期末按当前活期0.05%暂估。按共同计划期单利年化，不使用收益上限或区间平均；未计个人适用税费');
    warnings.push('到账日按周末顺延，未内置未来法定节假日日历；遇假期须再次核对');
  }
  if(p.kind==='savings'){
    locked=dayDiff(AS_OF,p.maturity);hold=locked;liquidity=10;
    if(locked>maxLock||days<locked)reasons.push(`严格本金模式须持有至${p.maturity}；提前兑取可能扣本金1‰手续费`);
    if(s.online)warnings.push('电子渠道购买资格需核对；提前兑取只能柜面，本模型不允许提前兑取');
    pending.push('票面利率已核验，但未核验购买日全价、完整现金流及当日额度；票面利率不直接代替共同计划期收益评分');
    rate=null;
    warnings.push('仅展示票面年利率与持有到期条件；未核验购买日现金流前不计算总分，不与共同计划期存款收益混排');
  }
  let capacity=s.amount;
  const bankExisting=p.issuer==='兴业银行'?(s.existingCib||0):s.existing;
  if(p.risk==='insured'){
    const reserveRate=p.upper??p.rate??1.3;
    const reserveDays=Math.max(p.termDays||p.months&&term||365,days);
    const cap=Math.floor(Math.max(0,500000-bankExisting)/(1+reserveRate/100*reserveDays/365)*100)/100;
    capacity=Math.min(s.amount,cap);
    if(p.kind==='structured'&&capacity>=p.min)capacity=p.min+Math.floor((capacity-p.min)/1000)*1000;
    if(p.min&&p.min>cap)reasons.push('单家银行本息保险额度不足最低认购额，不能靠本行分笔解决');
    if(!s.split&&s.amount>cap)reasons.push('全部资金放单一银行会超本息50万元保障边界');
    if(s.amount>cap&&s.split)warnings.push('只对本行保险额度内的一部分评分和测算；剩余资金须另找不同投保法人并分别核价');
  }
  if(p.maxAmount){capacity=Math.min(capacity,p.maxAmount);if(s.amount>capacity&&!s.split)reasons.push('超过本期每账户购买限额');}
  if(s.online&&p.kind==='demand')warnings.push('需已有正常可用的电子银行账户；系统、账户风控、银行卡限额均可能限制划转');
  const coverage=s.amount>0?clamp(capacity/s.amount*100,0,100):0;
  const scorable=Number.isFinite(rate)&&['insured','sovereign'].includes(p.risk);
  const dimensions={returns:scorable?clamp(rate/2*100,0,100):0,liquidity,ease,coverage,evidence};
  const weights=normaliseWeights(s.weights);
  const score=scorable?DIMENSIONS.reduce((sum,[key],i)=>sum+dimensions[key]*weights[i]/100,0):null;
  const status=reasons.length?'excluded':pending.length?'pending':'eligible';
  const interest= p.kind==='savings'?null:scorable?capacity*rate/100*days/365:null;
  return {...p,rateEffective:rate,term,hold,locked,capacity,bankExisting,dimensions,score,status,reasons,pending,warnings,interest,weights};
}
export function rank(products,state){return products.map(p=>evaluate(p,state)).sort((a,b)=>((b.score??-1)-(a.score??-1))||a.name.localeCompare(b.name,'zh-CN'));}
export function repoEstimate({amount,rate,interestDays,occupiedDays,feePer100k}){
  const fee=amount/100000*feePer100k,gross=amount*rate/100*interestDays/365,net=gross-fee;
  return {gross,fee,net,annual:net/amount*365/occupiedDays*100,breakEven:fee/amount*365/interestDays*100};
}
