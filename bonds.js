import {addMonths,parseDay,dayDiff,safeURL} from './core.js';

const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const words={
  en:{title:'Stocks & bonds',intro:'Bond yields affect stock valuations, financing costs and the economic outlook. Read the reason behind a move, not just its direction.',y2:'2-year Treasury',y10:'10-year Treasury',real:'10-year real yield',curve:'10Y minus 2Y',credit:'Corporate credit spread',daily:'Daily observations',monthly:'Monthly · GZ research',asOf:'Observed',change:'vs 5 observations earlier',monthChange:'vs prior month',pending:'Data not available',check:'Source check',retained:'Check unavailable · prior observations retained',aging:'Observation needs a fresh check',units:'Yields are annualized percentages. 1 basis point (bp) = 0.01 percentage point. The curve and credit spread are shown in bp.',chart:'Treasury yields · last three months',chartNote:'Historical observations, not a forecast. Weekends and holidays have no new observation. Hover over a point for its date and values.',source:'Source',creditNote:'GZ is a broad corporate credit-spread research series from Federal Reserve staff. It is monthly, can be revised and is not a company-specific borrowing rate or a daily high-yield index. Do not treat monthly and daily changes as simultaneous observations.',creditLink:'Open the daily high-yield spread at FRED',creditLinkNote:'External reference; its values are not reproduced here.',meaning:'What the indicators help explain',meaning2:'2-year yield: policy-rate expectations, with other market influences.',meaning10:'10-year yield: longer-term growth, inflation and term premium; a reference for financing and valuation.',meaningReal:'Real yield: inflation-linked Treasury yield; a useful lens on the discount rate applied to future cash flows.',meaningCurve:'10Y–2Y: the curve slope. Inversion can signal concern, but neither inversion nor steepening guarantees a recession or recovery.',meaningCredit:'Credit spread: the premium over comparable Treasury rates. Wider spreads can reflect greater credit or liquidity risk.',scenarios:'The same rate move can mean different things',scenarioFoot:'These are conditional scenarios, not a diagnosis of the current economy.',soft:'Inflation cools; growth holds up',softBody:'Yields fall and credit spreads stay stable or narrow. Lower discount rates may support stocks if earnings remain resilient.',recession:'Growth deteriorates',recessionBody:'Treasury yields fall but credit spreads widen. Safer bonds may rise while stocks face earnings and financing pressure.',inflation:'Inflation or the term premium rises',inflationBody:'Yields rise. Existing fixed-rate bond prices and stock valuations can both face pressure; stronger growth may offset some of the equity impact.',framework:'Bond transmission · analysis framework',watch:'What to check',caution:'Interpretation limit',details:'Explore the bond backdrop',snapshot:'Bond backdrop',noAuto:'This context does not automatically change the investment assessment.',primary:'How interest rates reach stocks',fixed:'Higher market rates first affect new debt, refinancing and floating-rate debt. Existing fixed-rate coupons do not automatically reset.',reviewed:'Framework reviewed',seriesStale:'Some observations are old or their source checks failed. Dates below remain the original observation dates.'},
  zh:{title:'股债环境',intro:'债券收益率会影响股票估值、融资成本和经济预期。判断影响时，需要看变化的原因。',y2:'2年期美国国债',y10:'10年期美国国债',real:'10年期实际收益率',curve:'10年－2年利差',credit:'企业信用利差',daily:'日度观测',monthly:'月度 · GZ研究',asOf:'观测',change:'较5个观测日前',monthChange:'较上月',pending:'暂无可用数据',check:'来源检查',retained:'本次检查未完成 · 保留原观测',aging:'观测数据需要重新检查',units:'收益率按年化百分比显示。1基点（bp）＝0.01个百分点。期限利差和信用利差以基点显示。',chart:'美国国债收益率 · 过去三个月',chartNote:'历史观测，不是预测。周末和假日没有新观测；悬停在点上可查看日期和数值。',source:'来源',creditNote:'GZ是美联储研究人员编制的企业信用利差序列，按月发布且可能修订；不是某家公司的融资报价，也不是每日高收益债指数，不能将该月度观测当作当天信用变化。',creditLink:'前往FRED查看每日高收益债利差',creditLinkNote:'外部参考，此处不转载该指数数值。',meaning:'这些指标分别看什么',meaning2:'2年期收益率：观察政策利率预期，同时也受其他市场因素影响。',meaning10:'10年期收益率：反映长期增长、通胀与期限溢价，是融资与估值的重要参考。',meaningReal:'实际收益率：通胀保值国债的收益率，可帮助判断未来现金流的折现压力。',meaningCurve:'10年－2年利差：观察收益率曲线形状。倒挂或曲线变陡，都不能单独证明衰退或复苏。',meaningCredit:'信用利差：企业相对可比国债支付的额外收益补偿。扩大可能意味着信用或流动性风险增加。',scenarios:'同样是利率变化，含义可能不同',scenarioFoot:'以下是条件情景，不代表对当前经济状态的自动判断。',soft:'通胀降温，增长保持',softBody:'收益率下降，信用利差稳定或收窄。如果盈利保持韧性，折现率下降可能支持股票。',recession:'经济增长恶化',recessionBody:'国债收益率下降，但信用利差扩大。避险债券可能上涨，股票却可能承受盈利和融资压力。',inflation:'通胀或期限溢价上升',inflationBody:'收益率上升，存量固定利率债券价格和股票估值都可能承压；若增长更强，也可能抵消部分股市压力。',framework:'债市传导路径 · 分析框架',watch:'重点核对',caution:'判断边界',details:'查看股债环境',snapshot:'股债环境',noAuto:'这些背景不会自动改写个股投资判断。',primary:'利率如何影响股票',fixed:'市场利率变化首先影响新融资、再融资和浮动利率债务。存量固定利率债务的票息不会自动重设。',reviewed:'框架复核',seriesStale:'部分观测较旧或来源检查未成功；下方仍显示原始观测日期。'}
};
const fieldText=(item,key,lang)=>lang==='zh'?(item?.[key+'Zh']||item?.[key]||''):(item?.[key]||'');
const number=(value,digits=2)=>Number.isFinite(value)?value.toFixed(digits):'—';
function environment(lang,today){
  const l=words[lang]||words.en;
  const fmt=(date,monthly=false)=>new Intl.DateTimeFormat(lang==='zh'?'zh-CN':'en-US',{timeZone:'UTC',year:'numeric',month:monthly?'long':'short',...(monthly?{}:{day:'numeric'})}).format(parseDay(date));
  return {l,fmt,today,lang};
}

export function bondMetrics(bonds={}){
  const spec=[['y2','nominal','yield2',false],['y10','nominal','yield10',false],['real','real','real10',false],['curve','nominal','curve',true],['credit','credit','spread',true]];
  return spec.map(([id,kind,field,inBps])=>{
    const group=bonds[kind]||{},rows=(group.observations||[]).map(row=>({date:row.date,value:field==='curve'?(Number.isFinite(row.yield10)&&Number.isFinite(row.yield2)?row.yield10-row.yield2:NaN):row[field]})).filter(r=>Number.isFinite(r.value)).sort((a,b)=>a.date.localeCompare(b.date));
    const latest=rows.at(-1),monthly=kind==='credit',prior=rows.at(monthly?-2:-6);
    return {id,kind,monthly,inBps,value:latest?latest.value*(inBps?100:1):null,date:latest?.date,delta:latest&&prior?Math.round((latest.value-prior.value)*10000)/100:null,priorDate:prior?.date,status:group.status||'pending',sourceUrl:group.sourceUrl,lastSuccessAt:group.lastSuccessAt};
  });
}
function oldMetric(metric,today){return metric.date&&dayDiff(metric.date,today)>(metric.monthly?95:7);}
function metricCard(metric,env){
  const {l,fmt,today}=env,unavailable=metric.status!=='ok',old=oldMetric(metric,today);
  return `<article class="bond-metric"><h3>${l[metric.id]}</h3><strong>${number(metric.value,metric.inBps?1:2)}<small>${metric.inBps?'bp':'%'}</small></strong><div class="bond-change">${metric.delta===null?'—':`${metric.delta>0?'+':''}${number(metric.delta,1)} bp`} <span>${l[metric.monthly?'monthChange':'change']}</span></div><p>${metric.date?`${l.asOf} ${fmt(metric.date,metric.monthly)}`:l.pending}</p><small>${l[metric.monthly?'monthly':'daily']}</small>${unavailable||old?`<p class="bond-note-warning">${l[old?'aging':'retained']}</p>`:''}</article>`;
}
function yieldChart(bonds,env){
  const {l,fmt,today}=env,start=addMonths(today,-3);
  const rows=(bonds?.nominal?.observations||[]).filter(r=>r.date>=start&&r.date<=today&&Number.isFinite(r.yield2)&&Number.isFinite(r.yield10));
  if(rows.length<2)return `<p>${l.pending}</p>`;
  function draw(width,mobile=false){
  const height=270,left=54,right=24,top=20,bottom=40;
  const values=rows.flatMap(r=>[r.yield2,r.yield10]);
  const low=Math.floor((Math.min(...values)-.08)*4)/4,high=Math.ceil((Math.max(...values)+.08)*4)/4;
  const x=date=>left+(parseDay(date)-parseDay(start))/(parseDay(today)-parseDay(start))*(width-left-right);
  const y=value=>top+(high-value)/(high-low)*(height-top-bottom);
  let drawing='';
  for(let i=0;i<=4;i++){const value=low+(high-low)*i/4;drawing+=`<line x1="${left}" x2="${width-right}" y1="${y(value)}" y2="${y(value)}" class="bond-grid-line"/><text x="${left-10}" y="${y(value)+4}" text-anchor="end">${number(value)}%</text>`;}
  for(const [field,color] of [['yield2','#3266ad'],['yield10','#187b69']]){
    drawing+=`<polyline fill="none" stroke="${color}" stroke-width="2.5" points="${rows.map(r=>`${x(r.date).toFixed(1)},${y(r[field]).toFixed(1)}`).join(' ')}"/>`;
    for(const r of rows)drawing+=`<circle cx="${x(r.date).toFixed(1)}" cy="${y(r[field]).toFixed(1)}" r="3" fill="${color}"><title>${esc(fmt(r.date))} · ${l[field==='yield2'?'y2':'y10']} ${number(r[field])}%</title></circle>`;
  }
  const dates=[rows[0].date,rows[Math.floor(rows.length/2)].date,rows.at(-1).date];
  for(const [index,date] of dates.entries()){
    const label=mobile?new Intl.DateTimeFormat(env.lang==='zh'?'zh-CN':'en-US',{timeZone:'UTC',month:'short',day:'numeric'}).format(parseDay(date)):fmt(date);
    drawing+=`<text x="${x(date)}" y="${height-12}" text-anchor="${index===0?'start':index===2?'end':'middle'}">${esc(label)}</text>`;
  }
  return `<svg class="bond-chart ${mobile?'bond-chart-mobile':'bond-chart-desktop'}" viewBox="0 0 ${width} ${height}" role="img" aria-label="${l.chart}"><title>${l.chart}</title><desc>${l.chartNote}</desc>${drawing}</svg>`;
  }
  return `${draw(820)}${draw(420,true)}<div class="bond-chart-legend"><span><i class="line-two"></i>${l.y2}</span><span><i class="line-ten"></i>${l.y10}</span></div>`;
}

export function bondDashboard(bonds={},lang='en',today){
  const env=environment(lang,today),{l,fmt}=env,metrics=bondMetrics(bonds);
  const nominal=bonds.nominal||{},real=bonds.real||{},credit=bonds.credit||{};
  return `<div class="info-banner">${l.intro}</div>${metrics.some(m=>m.status!=='ok'||oldMetric(m,today))?`<p class="bond-note-warning">${l.seriesStale}</p>`:''}<div class="bond-metrics">${metrics.map(m=>metricCard(m,env)).join('')}</div><p class="bond-units">${l.units}</p><section class="bond-chart-card"><h2>${l.chart}</h2>${yieldChart(bonds,env)}<p>${l.chartNote}</p><div class="bond-source-row"><a href="${esc(safeURL(nominal.sourceUrl))}" target="_blank" rel="noopener noreferrer">${l.source}: US Treasury</a><span>${l.check}: ${nominal.lastSuccessAt?new Intl.DateTimeFormat(lang==='zh'?'zh-CN':'en-US',{timeZone:'America/New_York',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}).format(new Date(nominal.lastSuccessAt))+' ET':'—'}</span></div><details class="bond-observations"><summary>${lang==='zh'?'查看最近5次观测':'See the last five observations'}</summary><table><thead><tr><th>${l.asOf}</th><th>2Y</th><th>10Y</th><th>10Y–2Y</th></tr></thead><tbody>${(nominal.observations||[]).slice(-5).reverse().map(r=>`<tr><td>${fmt(r.date)}</td><td>${number(r.yield2)}%</td><td>${number(r.yield10)}%</td><td>${number((r.yield10-r.yield2)*100,1)} bp</td></tr>`).join('')}</tbody></table></details></section><div class="bond-explanation-grid"><section class="bond-explanation"><h2>${l.meaning}</h2><ul>${['meaning2','meaning10','meaningReal','meaningCurve','meaningCredit'].map(key=>`<li>${l[key]}</li>`).join('')}</ul><p>${l.fixed}</p><a href="https://www.federalreserve.gov/newsevents/speech/jefferson20231009a.htm" target="_blank" rel="noopener noreferrer">${l.primary}</a></section><section class="bond-explanation"><h2>${l.credit}</h2><p>${l.creditNote}</p><a href="${esc(safeURL(credit.sourceUrl))}" target="_blank" rel="noopener noreferrer">${l.source}: Federal Reserve GZ / EBP</a><p class="bond-credit-external"><a href="https://fred.stlouisfed.org/series/BAMLH0A0HYM2" target="_blank" rel="noopener noreferrer">${l.creditLink}</a><small>${l.creditLinkNote}</small></p><a href="${esc(safeURL(real.sourceUrl))}" target="_blank" rel="noopener noreferrer">${l.source}: Treasury real yields</a></section></div><section class="bond-scenarios"><h2>${l.scenarios}</h2><p>${l.scenarioFoot}</p><div>${['soft','recession','inflation'].map(s=>`<article><h3>${l[s]}</h3><p>${l[s+'Body']}</p></article>`).join('')}</div></section>`;
}

export function bondTeaser(bonds={},lang='en',today){
  const {l,fmt}=environment(lang,today),metric=bondMetrics(bonds).find(m=>m.id==='y10');
  return `<div class="bond-teaser"><div><strong>${l.snapshot}</strong><span>${l.y10} ${number(metric.value)}%${metric.date?' · '+fmt(metric.date):''}${metric.status!=='ok'||oldMetric(metric,today)?' · '+l.aging:''}</span></div><button data-view="bonds">${l.details}</button></div>`;
}

export function bondStockContext(stock,bonds={},lang='en',today){
  const {l,fmt}=environment(lang,today),exposure=stock.bondExposure;
  const relevant=bondMetrics(bonds).filter(m=>['y10','real','credit'].includes(m.id));
  return `<section class="stock-bond-context"><h3>${l.framework}</h3>${exposure?`<p>${esc(fieldText(exposure,'summary',lang))}</p><h4>${l.watch}</h4><p>${esc(fieldText(exposure,'watch',lang))}</p><h4>${l.caution}</h4><p>${esc(fieldText(exposure,'caution',lang))}</p>`:`<p>${l.intro}</p>`}<div class="stock-bond-values">${relevant.map(m=>`<span><b>${l[m.id]} ${number(m.value,m.inBps?1:2)} ${m.inBps?'bp':'%'}</b><small>${m.date?fmt(m.date,m.monthly):l.pending}${m.status!=='ok'||oldMetric(m,today)?' · '+l.aging:''}</small></span>`).join('')}</div>${exposure?.sourceUrl?`<a href="${esc(safeURL(exposure.sourceUrl))}" target="_blank" rel="noopener noreferrer">${l.source}</a>`:''}<button data-view="bonds">${l.details}</button><p class="stock-bond-foot">${l.noAuto}</p></section>`;
}
