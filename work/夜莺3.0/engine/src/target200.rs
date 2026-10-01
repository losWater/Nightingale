
use std::sync::OnceLock;
use std::collections::HashMap;
use crate::编码信息;
use crate::objectives::default::默认目标函数参数;
#[derive(serde::Deserialize)]struct Target{weight:f64,indices:Vec<usize>}
struct Data{targets:Vec<Target>,matrix:HashMap<String,f64>,weight:f64}
static DATA:OnceLock<Option<Data>>=OnceLock::new();
pub fn penalty(rows:&[编码信息],p:&默认目标函数参数)->f64{
 let d=DATA.get_or_init(||{
  let base=std::env::var("NIGHTINGALE_TARGET_DIR").ok()?;
  let weight=std::env::var("NIGHTINGALE_TARGET_WEIGHT").unwrap().parse().unwrap();
  Some(Data{targets:serde_json::from_str(&std::fs::read_to_string(format!("{base}/targets.json")).unwrap()).unwrap(),matrix:serde_json::from_str(&std::fs::read_to_string(format!("{base}/matrix.json")).unwrap()).unwrap(),weight})
 });
 let Some(d)=d else{return 0.0};if d.weight==0.0{return 0.0}
 let mut total=0.0;let mut den=0.0;
 for t in &d.targets{
  let mut best:Option<(usize,String,u8)>=None;
  for &i in &t.indices{for v in [&rows[i].全码,&rows[i].简码]{
   let mut n=v.原始编码;let mut c=String::new();while n>0{c.push(*p.数字转键.get(&(n%p.进制)).unwrap());n/=p.进制;}
   if c.is_empty(){continue}let candidate=(c.len(),c,v.原始编码候选位置);if best.as_ref().map_or(true,|b|candidate<*b){best=Some(candidate)}
  }}
  let (len,mut c,rank)=best.unwrap();if len<4||rank>0{c.push(" ;'456789".chars().nth(rank as usize).unwrap_or('9'));}
  let chars:Vec<_>=c.chars().collect();let cost:f64=chars.windows(2).map(|v|d.matrix[&v.iter().collect::<String>()]).sum();
  total+=cost/(chars.len()-1) as f64*t.weight;den+=t.weight;
 }d.weight*total/den
}
