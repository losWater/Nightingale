//! 夜桜附加目标项（NIGHTINGALE_YOZAKURA 指向 JSON 配置时启用；未设置则为 0，旧语义不变）。
//!
//! 每次计算都从当前编码结果全量重算，不依赖增量缓存：
//! - 独占码位：层级集合内的读音，若全码与任一“键位无关签名”不同的读音同码，记一次违例。
//! - 三四码负荷：全码第 3、4 码按频率合并计数，对目标份额单侧超载求平方和；另对 p 类观察键排名设门禁。
//! - 分段当量：第 2→3 码、第 3→4 码，按频率加权平均（当量矩阵）。
//! - 互斥：指定两个读音的指定码位不得同键（虫／鸟）。
use std::collections::HashMap;
use std::sync::OnceLock;

use crate::objectives::default::默认目标函数参数;
use crate::编码信息;

#[derive(serde::Deserialize)]
struct Tier {
    indices: Vec<usize>,
    weight: f64,
    /// true：仅当有更常用（元素序号更小）且签名不同的读音同码才算违例（有效重码口径）
    #[serde(default)]
    effective: bool,
    /// 分档当量用：true 时档内按读音频率加权（否则不加权平均）
    #[serde(default)]
    weighted: bool,
    /// 允许的违例数，超出部分才计罚（用于“前3571 有效重码 ≤9”硬门禁）
    #[serde(default)]
    allow: usize,
}

#[derive(serde::Deserialize)]
struct Mutex {
    a: usize,
    b: usize,
    position: usize,
    weight: f64,
}

#[derive(serde::Deserialize)]
struct Config {
    /// 参与统计的读音条目数（元素表前 n 条，排除固定简词占位）
    n: usize,
    /// 每条读音的键位无关签名编号（音节 + 首末根组）
    signature: Vec<u32>,
    frequency: Vec<f64>,
    exclusive: Vec<Tier>,
    /// 26 键目标份额（第 3、4 码合并）
    target_share: HashMap<char, f64>,
    overload_weight: f64,
    /// 排名门禁：键 → 最高允许名次（如 p → 21 表示须排第 21 名或更后）
    rank_gate: HashMap<char, usize>,
    rank_gate_weight: f64,
    eq23_weight: f64,
    eq34_weight: f64,
    mutex: Vec<Mutex>,
    matrix: String,
    /// 分档当量（作者 2026-10-01）：若提供，E₂₃/E₃₄ 改为各档内不加权平均、再按档权合成；
    /// 档内只含需要用到形码的读音（固定一二简读音已在生成配置时排除）。
    #[serde(default)]
    eq_bins: Vec<Tier>,
    /// 形码成本（作者 2026-10-01）：只算形码管得到的读音（排除固定一二简）；
    /// 三简读音成本 = 2→3 当量；打全码读音成本 = (2→3 + 3→4)/2。
    /// 前1500 档不加权平均，1500 以后按频率加权，两者按 top_share 合成。
    #[serde(default)]
    shape: Option<ShapeCfg>,
    /// 字词撞码（作者 2026-10-01）：只算二字词；读音有一二三简则不算；必须打全码者全码等于词码即撞。
    #[serde(default)]
    word_clash: Vec<ClashRule>,
}

#[derive(serde::Deserialize)]
struct ClashRule {
    chars: Vec<usize>,
    words: Vec<String>,
    weight: f64,
    /// 允许的撞码数；超出部分每个罚 weight（作者 2026-10-01：规则③设为硬约束 ≤ 5）
    #[serde(default)]
    allow: usize,
}

#[derive(serde::Deserialize)]
struct ShapeCfg {
    top: Vec<usize>,
    rest: Vec<usize>,
    top_share: f64,
    weight: f64,
    /// 门禁：four_idx 中打四码的读音数 ≤ four_max；san_idx 中三简读音数 ≥ san_min
    four_idx: Vec<usize>,
    four_max: usize,
    san_idx: Vec<usize>,
    san_min: usize,
    /// 四码门禁（硬）每超一个的罚分
    gate_weight: f64,
    /// 三简软约束：每少一个的罚分（作者：3600 为软约束）
    #[serde(default)]
    san_weight: f64,
    /// p 软约束：形码读音（按频率）形码按键中 p 的占比超过 p_cap 的部分 × p_weight
    #[serde(default)]
    p_cap: f64,
    #[serde(default)]
    p_weight: f64,
}

struct Data {
    c: Config,
    /// 字词撞码规则的词码集合（与 c.word_clash 同序）
    clash_codes: Vec<rustc_hash::FxHashSet<u64>>,
    /// 当量表按键编号展开：eq[a * radix + b]
    eq: Vec<f64>,
    radix: usize,
    /// 目标份额、排名门禁按键编号
    share: Vec<f64>,
    gate: Vec<(usize, usize)>,
    key_of: Vec<char>,
}

static DATA: OnceLock<Option<Data>> = OnceLock::new();

thread_local! {
    static SCRATCH: std::cell::RefCell<rustc_hash::FxHashMap<u64, (usize, u32, usize)>> =
        std::cell::RefCell::new(rustc_hash::FxHashMap::default());
}

fn data(p: &默认目标函数参数) -> Option<&'static Data> {
    DATA.get_or_init(|| {
        let path = std::env::var("NIGHTINGALE_YOZAKURA").ok()?;
        let c: Config = serde_json::from_str(&std::fs::read_to_string(&path).expect("读取夜桜配置失败"))
            .expect("解析夜桜配置失败");
        let raw: HashMap<String, f64> =
            serde_json::from_str(&std::fs::read_to_string(&c.matrix).expect("读取当量矩阵失败"))
                .expect("解析当量矩阵失败");
        assert_eq!(c.signature.len(), c.n);
        assert_eq!(c.frequency.len(), c.n);
        let radix = p.进制 as usize;
        let mut key_of = vec!['\0'; radix];
        for (&d, &k) in &p.数字转键 {
            key_of[d as usize] = k;
        }
        let mut eq = vec![1.3; radix * radix];
        for a in 0..radix {
            for b in 0..radix {
                let mut s = String::new();
                s.push(key_of[a]);
                s.push(key_of[b]);
                if let Some(v) = raw.get(&s) {
                    eq[a * radix + b] = *v;
                }
            }
        }
        let mut share = vec![0.0; radix];
        for d in 0..radix {
            share[d] = c.target_share.get(&key_of[d]).copied().unwrap_or(1.0 / 26.0);
        }
        let gate = c
            .rank_gate
            .iter()
            .map(|(k, &r)| ((0..radix).find(|&d| key_of[d] == *k).unwrap(), r))
            .collect();
        let digit = |k: char| (0..radix).find(|&d| key_of[d] == k).unwrap() as u64;
        let clash_codes = c
            .word_clash
            .iter()
            .map(|rule| {
                rule.words
                    .iter()
                    .map(|w| {
                        let (mut v, mut m) = (0u64, 1u64);
                        for ch in w.chars() {
                            v += digit(ch) * m;
                            m *= radix as u64;
                        }
                        v
                    })
                    .collect()
            })
            .collect();
        Some(Data { c, clash_codes, eq, radix, share, gate, key_of })
    })
    .as_ref()
}

#[derive(Default, Debug, Clone)]
pub struct 形码分项 {
    pub p_share: f64,
    pub top: f64,
    pub rest: f64,
    pub cost: f64,
    pub four_top: usize,
    pub san: usize,
}

#[derive(Default, Debug, Clone)]
pub struct 分项 {
    pub shape: Option<形码分项>,
    pub clashes: Vec<usize>,
    pub exclusive_violations: Vec<usize>,
    pub overload: f64,
    pub rank_excess: f64,
    pub eq23: f64,
    pub eq34: f64,
    pub mutex_violations: usize,
    pub total: f64,
}

pub fn 计算(rows: &[编码信息], p: &默认目标函数参数) -> Option<分项> {
    let d = data(p)?;
    let c = &d.c;
    let r = d.radix as u64;
    let mut out = 分项::default();

    // 独占码位：每个码记 (最小序号 m1, 其签名 s1, 签名不同于 s1 的最小序号 m2)
    SCRATCH.with(|cell| {
        let mut map = cell.borrow_mut();
        map.clear();
        for i in 0..c.n {
            let code = rows[i].全码.原始编码;
            let si = c.signature[i];
            map.entry(code)
                .and_modify(|e| {
                    if e.2 == usize::MAX && si != e.1 {
                        e.2 = i;
                    }
                })
                .or_insert((i, si, usize::MAX));
        }
        for tier in &c.exclusive {
            let mut v = 0usize;
            for &i in &tier.indices {
                let (m1, s1, m2) = map[&rows[i].全码.原始编码];
                let si = c.signature[i];
                let hit = if si != s1 {
                    // 最小序号者签名不同，且必在 i 之前
                    let _ = m1;
                    true
                } else if tier.effective {
                    m2 < i
                } else {
                    m2 != usize::MAX
                };
                if hit {
                    v += 1;
                }
            }
            out.exclusive_violations.push(v);
            out.total += tier.weight * v as f64;
        }
    });

    // 三四码负荷与分段当量（全码四位：个位为第 1 码）
    let mut use_ = vec![0.0f64; d.radix];
    let (mut e23, mut e34, mut w) = (0.0, 0.0, 0.0);
    for i in 0..c.n {
        let code = rows[i].全码.原始编码;
        if code < r * r * r {
            continue;
        }
        let k2 = ((code / r) % r) as usize;
        let k3 = ((code / (r * r)) % r) as usize;
        let k4 = ((code / (r * r * r)) % r) as usize;
        let f = c.frequency[i];
        use_[k3] += f;
        use_[k4] += f;
        e23 += f * d.eq[k2 * d.radix + k3];
        e34 += f * d.eq[k3 * d.radix + k4];
        w += f;
    }
    if w > 0.0 {
        out.eq23 = e23 / w;
        out.eq34 = e34 / w;
        if !c.eq_bins.is_empty() {
            let (mut s23, mut s34, mut sw) = (0.0, 0.0, 0.0);
            for bin in &c.eq_bins {
                let (mut a, mut b, mut k, mut kw) = (0.0, 0.0, 0usize, 0.0);
                for &i in &bin.indices {
                    let code = rows[i].全码.原始编码;
                    if code < r * r * r {
                        continue;
                    }
                    let k2 = ((code / r) % r) as usize;
                    let k3 = ((code / (r * r)) % r) as usize;
                    let k4 = ((code / (r * r * r)) % r) as usize;
                    let fw = if bin.weighted { c.frequency[i] } else { 1.0 };
                    a += fw * d.eq[k2 * d.radix + k3];
                    b += fw * d.eq[k3 * d.radix + k4];
                    k += 1;
                    kw += fw;
                }
                if k > 0 && kw > 0.0 {
                    s23 += bin.weight * a / kw;
                    s34 += bin.weight * b / kw;
                    sw += bin.weight;
                }
            }
            out.eq23 = s23 / sw;
            out.eq34 = s34 / sw;
        }
        let mut shares: Vec<(usize, f64)> = (0..d.radix)
            .filter(|&k| d.key_of[k].is_ascii_lowercase())
            .map(|k| (k, use_[k] / (2.0 * w)))
            .collect();
        for &(k, u) in &shares {
            let excess = (u - d.share[k]).max(0.0);
            out.overload += excess * excess;
        }
        if !d.gate.is_empty() {
            shares.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
            for &(k, min_rank) in &d.gate {
                let u = shares.iter().find(|x| x.0 == k).unwrap().1;
                let bar = shares[min_rank - 1].1;
                out.rank_excess += (u - bar).max(0.0);
            }
        }
    }
    out.total += c.overload_weight * out.overload * 1e4
        + c.rank_gate_weight * out.rank_excess * 1e2
        + c.eq23_weight * out.eq23
        + c.eq34_weight * out.eq34;

    if let Some(sc) = &c.shape {
        let r2 = r * r;
        let r3 = r2 * r;
        // 返回 (成本, 是否三简, 是否四码)
        let cost = |i: usize| -> (f64, bool, bool) {
            let full = rows[i].全码.原始编码;
            let short = rows[i].简码.原始编码;
            let k2 = ((full / r) % r) as usize;
            let k3 = ((full / r2) % r) as usize;
            let k4 = ((full / r3) % r) as usize;
            let e23 = d.eq[k2 * d.radix + k3];
            let e34 = d.eq[k3 * d.radix + k4];
            let san = short >= r2 && short < r3 && short != full;
            let shorter = short > 0 && short < r3 && short != full;
            if san { (e23, true, false) } else { ((e23 + e34) / 2.0, false, !shorter) }
        };
        let mut x = 形码分项::default();
        let mut a = 0.0;
        for &i in &sc.top { a += cost(i).0; }
        x.top = if sc.top.is_empty() { 0.0 } else { a / sc.top.len() as f64 };
        let (mut b, mut bw) = (0.0, 0.0);
        for &i in &sc.rest { let fi = c.frequency[i]; b += fi * cost(i).0; bw += fi; }
        x.rest = if bw > 0.0 { b / bw } else { 0.0 };
        x.cost = sc.top_share * x.top + (1.0 - sc.top_share) * x.rest;
        x.four_top = sc.four_idx.iter().filter(|&&i| cost(i).2).count();
        if sc.p_weight > 0.0 {
            let pk = d.key_of.iter().position(|&k| k == 'p').unwrap() as u64;
            let (mut pp, mut tt) = (0.0, 0.0);
            for &i in sc.top.iter().chain(sc.rest.iter()) {
                let fi = c.frequency[i];
                let full = rows[i].全码.原始编码;
                let k3 = (full / r2) % r;
                let k4 = (full / r3) % r;
                if cost(i).1 {
                    tt += fi;
                    if k3 == pk { pp += fi; }
                } else {
                    tt += 2.0 * fi;
                    if k3 == pk { pp += fi; }
                    if k4 == pk { pp += fi; }
                }
            }
            x.p_share = if tt > 0.0 { pp / tt } else { 0.0 };
            out.total += sc.p_weight * (x.p_share - sc.p_cap).max(0.0);
        }
        x.san = sc.san_idx.iter().filter(|&&i| cost(i).1).count();
        out.total += sc.weight * x.cost
            + sc.gate_weight * (x.four_top.saturating_sub(sc.four_max) as f64)
            + sc.san_weight * (sc.san_min.saturating_sub(x.san) as f64);
        out.shape = Some(x);
    }

    {
        let r3 = r * r * r;
        for (rule, codes) in c.word_clash.iter().zip(&d.clash_codes) {
            let mut v = 0usize;
            for &i in &rule.chars {
                let full = rows[i].全码.原始编码;
                let short = rows[i].简码.原始编码;
                let shorter = short > 0 && short < r3 && short != full;
                if !shorter && codes.contains(&full) {
                    v += 1;
                }
            }
            out.clashes.push(v);
            out.total += rule.weight * v.saturating_sub(rule.allow) as f64;
        }
    }

    for m in &c.mutex {
        let pos = r.pow(m.position as u32);
        let (a, b) = (rows[m.a].全码.原始编码, rows[m.b].全码.原始编码);
        if a >= pos && b >= pos && (a / pos) % r == (b / pos) % r {
            out.mutex_violations += 1;
            out.total += m.weight;
        }
    }
    Some(out)
}

pub fn penalty(rows: &[编码信息], p: &默认目标函数参数) -> f64 {
    计算(rows, p).map_or(0.0, |x| x.total)
}

/// 编码结束时把分项写到 stderr，供外部核对（引擎 metric.json 结构不变）。
pub fn 报告(rows: &[编码信息], p: &默认目标函数参数) {
    if let Some(x) = 计算(rows, p) {
        eprintln!(
            "YOZAKURA exclusive={:?} overload={:.6e} rank_excess={:.6} eq23={:.6} eq34={:.6} mutex={} total={:.6}",
            x.exclusive_violations, x.overload, x.rank_excess, x.eq23, x.eq34, x.mutex_violations, x.total
        );
        if !x.clashes.is_empty() {
            eprintln!("YOZAKURA_CLASH {:?}", x.clashes);
        }
        if let Some(s) = &x.shape {
            eprintln!("YOZAKURA_SHAPE top={:.6} rest={:.6} cost={:.6} four_top={} san={} p_share={:.6}", s.top, s.rest, s.cost, s.four_top, s.san, s.p_share);
        }
    }
}
