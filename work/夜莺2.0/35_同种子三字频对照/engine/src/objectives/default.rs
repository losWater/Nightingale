use rustc_hash::FxHashMap;

use super::cache::缓存;
use super::metric::默认指标;
use super::metric::{交叉碰撞指标, 辅助码指标};
use super::目标函数;
use crate::config::部分权重;
use crate::contexts::default::{
    默认上下文, 默认决策, 默认决策变化, 默认决策空间
};
use crate::encoders::编码器;
use crate::错误;
use crate::{指法向量, 编码信息, 键位分布损失函数};

#[derive(Clone)]
pub struct 默认目标函数<E: 编码器> {
    pub 决策空间: 默认决策空间,
    pub 参数: 默认目标函数参数,
    pub 编码器: E,
    pub 编码结果: Vec<编码信息>,
    pub 计数桶列表: Vec<[Option<缓存>; 2]>,
    pub 字词交叉缓存: Option<字词交叉缓存>,
    pub 辅助码缓存: Option<辅助码缓存>,
}

#[derive(Clone)]
pub struct 字词交叉缓存 {
    targets: FxHashMap<u64, (f64, usize)>,
    character_factors: Vec<f64>,
    // The last full code that actually participated in cross-collision
    // accounting. Characters with a real shorter code are stored as None.
    character_codes: Vec<Option<u64>>,
    weight: f64,
    hard_penalty: f64,
    soft: f64,
    hard: i64,
}

#[derive(Clone)]
pub struct 辅助码记录 {
    first_index: usize,
    second_index: usize,
    weight: f64,
}

#[derive(Clone)]
pub struct 辅助码缓存 {
    weight: f64,
    radix: u64,
    records: Vec<辅助码记录>,
    groups: Vec<Vec<usize>>,
    character_groups: Vec<Vec<usize>>,
    group_burden: Vec<f64>,
    group_first_choice: Vec<u64>,
    group_first_choice_weight: Vec<f64>,
    total_weight: f64,
    burden: f64,
    first_choice: u64,
    first_choice_weight: f64,
}

impl 辅助码缓存 {
    #[inline]
    fn 首型(编码结果: &[编码信息], index: usize, radix: u64) -> u64 {
        (编码结果[index].全码.原始编码 / radix.pow(2)) % radix
    }

    fn 计算组(
        &self, group: usize, 编码结果: &[编码信息], radix: u64
    ) -> (f64, u64, f64) {
        let indices = &self.groups[group];
        let mut burden = 0.0;
        let mut first_choice = 0;
        let mut first_choice_weight = 0.0;
        for (position, &record_index) in indices.iter().enumerate() {
            let record = &self.records[record_index];
            let first_key = Self::首型(编码结果, record.first_index, radix);
            let second_key = Self::首型(编码结果, record.second_index, radix);
            // records 已按频次从高到低排列；筛选后的名次就是此前同键词数 + 1。
            let mut first_rank = 1u64;
            let mut second_rank = 1u64;
            for &previous_index in &indices[..position] {
                let previous = &self.records[previous_index];
                if Self::首型(编码结果, previous.first_index, radix) == first_key {
                    first_rank += 1;
                }
                if Self::首型(编码结果, previous.second_index, radix) == second_key {
                    second_rank += 1;
                }
            }
            let best_rank = first_rank.min(second_rank);
            burden += record.weight * (best_rank - 1) as f64;
            if best_rank == 1 {
                first_choice += 1;
                first_choice_weight += record.weight;
            }
        }
        (burden, first_choice, first_choice_weight)
    }

    fn 刷新(&mut self, changed: Option<&[usize]>, 编码结果: &[编码信息], radix: u64) {
        let groups: Vec<usize> = if let Some(changed) = changed {
            let mut result: Vec<_> = changed
                .iter()
                .filter(|&&index| index < self.character_groups.len())
                .flat_map(|&index| self.character_groups[index].iter().copied())
                .collect();
            result.sort_unstable();
            result.dedup();
            result
        } else {
            (0..self.groups.len()).collect()
        };
        if changed.is_none() {
            self.burden = 0.0;
            self.first_choice = 0;
            self.first_choice_weight = 0.0;
        }
        for group in groups {
            if changed.is_some() {
                self.burden -= self.group_burden[group];
                self.first_choice -= self.group_first_choice[group];
                self.first_choice_weight -= self.group_first_choice_weight[group];
            }
            let (burden, first_choice, first_choice_weight) =
                self.计算组(group, 编码结果, radix);
            self.group_burden[group] = burden;
            self.group_first_choice[group] = first_choice;
            self.group_first_choice_weight[group] = first_choice_weight;
            self.burden += burden;
            self.first_choice += first_choice;
            self.first_choice_weight += first_choice_weight;
        }
    }
}

#[derive(Clone)]
pub struct 默认目标函数参数 {
    pub 键位分布信息: Vec<键位分布损失函数>,
    pub 当量信息: Vec<f64>,
    /// 音码末键→首形键专用当量；与普通键对当量隔离。
    /// 夜莺采用 B=右手：同手为 1，换手为 0。
    pub transition_equivalence: Vec<f64>,
    pub 指法计数: Vec<指法向量>,
    pub 数字转键: FxHashMap<u64, char>,
    pub 正则化强度: f64,
    pub 进制: u64,
}

pub type Frequencies = Vec<f64>;

pub enum PartialType {
    CharactersFull,
    CharactersShort,
    WordsFull,
    WordsShort,
}

impl PartialType {
    pub fn is_characters(&self) -> bool {
        matches!(self, Self::CharactersFull | Self::CharactersShort)
    }
}

/// 目标函数
impl<E: 编码器<决策 = 默认决策>> 默认目标函数<E> {
    /// 通过传入配置表示、编码器和共用资源来构造一个目标函数
    pub fn 新建(上下文: &默认上下文, 编码器: E) -> Result<Self, 错误> {
        let 键位分布信息 = 上下文.棱镜.预处理键位分布信息(&上下文.键位分布信息);
        let 线性表长度 = 上下文.线性表长度();
        let 当量信息 = 上下文.棱镜.预处理当量信息(&上下文.当量信息, 线性表长度);
        let mut transition_equivalence = vec![0.0; 线性表长度];
        let hand = |key: char| {
            if "qwertasdfgzxcv".contains(key) { 0u8 }
            else if "yuiophjklbnm".contains(key) { 1u8 }
            else { 2u8 }
        };
        for (index, value) in transition_equivalence.iter_mut().enumerate() {
            let first = (index as u64) % 上下文.棱镜.进制;
            let second = ((index as u64) / 上下文.棱镜.进制) % 上下文.棱镜.进制;
            if let (Some(a), Some(b)) = (
                上下文.棱镜.数字转键.get(&first),
                上下文.棱镜.数字转键.get(&second),
            ) {
                let (ha, hb) = (hand(*a), hand(*b));
                *value = if ha < 2 && ha == hb { 1.0 } else { 0.0 };
            }
        }
        let 指法计数 = 上下文.棱镜.预处理指法标记(线性表长度);
        let config = 上下文
            .配置
            .optimization
            .as_ref()
            .ok_or("优化配置不存在")?
            .objective
            .clone();
        let 最大编码 = 当量信息.len() as u64;
        let 构造缓存 =
            |x: &部分权重| 缓存::new(x, 上下文.棱镜.进制, 上下文.词列表.len(), 最大编码);
        let 一字全码 = config.characters_full.as_ref().map(构造缓存);
        let 一字简码 = config.characters_short.as_ref().map(构造缓存);
        let 多字全码 = config.words_full.as_ref().map(构造缓存);
        let 多字简码 = config.words_short.as_ref().map(构造缓存);
        let 计数桶列表 = vec![[一字全码, 一字简码], [多字全码, 多字简码]];
        let 字词交叉缓存 = config.character_word_collision.as_ref().map(|cross| {
            let mut targets = FxHashMap::default();
            for (code, target) in &cross.targets {
                let mut number = 0u64;
                let mut multiplier = 1u64;
                for key in code.chars() {
                    number += 上下文.棱镜.键转数字[&key] * multiplier;
                    multiplier *= 上下文.棱镜.进制;
                }
                let hard_top = target.hard_character_top.unwrap_or_else(|| {
                    if target.hard {
                        cross.hard_character_top
                    } else {
                        0
                    }
                });
                targets.insert(number, (target.soft, hard_top));
            }
            let character_count = 上下文.词列表.iter().take_while(|x| x.词长 == 1).count();
            let mut character_factors = vec![0.0; character_count];
            for (index, factor) in character_factors.iter_mut().enumerate() {
                if let Some(tier) = cross.character_tiers.iter().find(|x| index < x.top) {
                    *factor = tier.factor;
                }
            }
            字词交叉缓存 {
                targets,
                character_codes: vec![None; character_count],
                character_factors,
                weight: cross.weight,
                hard_penalty: cross.hard_penalty,
                soft: 0.0,
                hard: 0,
            }
        });
        let 辅助码缓存 = config.auxiliary_two_char.as_ref().map(|auxiliary| {
            let group_count = auxiliary
                .records
                .iter()
                .map(|x| x.group)
                .max()
                .map_or(0, |x| x + 1);
            let mut groups = vec![Vec::new(); group_count];
            let mut character_groups = vec![Vec::new(); 上下文.词列表.len()];
            let mut records = Vec::with_capacity(auxiliary.records.len());
            let mut total_weight = 0.0;
            for (record_index, source) in auxiliary.records.iter().enumerate() {
                assert!(
                    source.first_index < 上下文.词列表.len(),
                    "辅助码首字索引越界"
                );
                assert!(
                    source.second_index < 上下文.词列表.len(),
                    "辅助码尾字索引越界"
                );
                groups[source.group].push(record_index);
                character_groups[source.first_index].push(source.group);
                character_groups[source.second_index].push(source.group);
                records.push(辅助码记录 {
                    first_index: source.first_index,
                    second_index: source.second_index,
                    weight: source.weight,
                });
                total_weight += source.weight;
            }
            for list in &mut character_groups {
                list.sort_unstable();
                list.dedup();
            }
            辅助码缓存 {
                weight: auxiliary.weight,
                radix: 上下文.棱镜.进制,
                records,
                groups,
                character_groups,
                group_burden: vec![0.0; group_count],
                group_first_choice: vec![0; group_count],
                group_first_choice_weight: vec![0.0; group_count],
                total_weight,
                burden: 0.0,
                first_choice: 0,
                first_choice_weight: 0.0,
            }
        });
        let 参数 = 默认目标函数参数 {
            键位分布信息,
            当量信息,
            transition_equivalence,
            指法计数,
            数字转键: 上下文.棱镜.数字转键.clone(),
            正则化强度: config.regularization_strength.unwrap_or(1.0),
            进制: 上下文.棱镜.进制,
        };
        let 编码结果: Vec<_> = 上下文.词列表.iter().map(编码信息::new).collect();
        Ok(Self {
            参数,
            编码器,
            编码结果: 编码结果.clone(),
            计数桶列表: 计数桶列表.clone(),
            字词交叉缓存,
            辅助码缓存,
            决策空间: 上下文.决策空间.clone(),
        })
    }

    pub fn 计算复杂度(&self, 决策: &默认决策) -> f64 {
        let mut 复杂度 = 0.0;
        for (序号, 安排列表) in self.决策空间.元素.iter().enumerate() {
            let 安排 = &决策.元素[序号];
            let mut 分值 = 0.0;
            for 条件安排 in 安排列表 {
                if &条件安排.安排 == 安排 {
                    分值 = 条件安排.分数;
                    break;
                }
            }
            复杂度 += 分值;
        }
        复杂度
    }
}

impl<E: 编码器<决策 = 默认决策>> 目标函数 for 默认目标函数<E> {
    type 目标值 = 默认指标;
    type 决策 = 默认决策;

    /// 计算各个部分编码的指标，然后将它们合并成一个指标输出
    fn 计算(
        &mut self, 决策: &默认决策, 决策变化: &Option<默认决策变化>
    ) -> (默认指标, f64) {
        let 参数 = &self.参数;
        self.编码器.编码(决策, 决策变化, &mut self.编码结果);
        // 必须在常规缓存清除“有变化”标记之前更新；这样每步只处理受本次根移动影响的字。
        if let Some(cross) = &mut self.字词交叉缓存 {
            let full_refresh = 决策变化.is_none();
            if full_refresh {
                // 初次计算／整体验算必须从当前全部编码重建缓存。旧实现仍按“有变化”
                // 过滤，导致从未受移动影响的既有字词碰撞永久漏计。
                cross.soft = 0.0;
                cross.hard = 0;
                cross.character_codes.fill(None);
            }
            let changed: Box<dyn Iterator<Item = usize>> = match self.编码器.变化词() {
                Some(indices) => Box::new(indices.iter().copied()),
                None => Box::new(0..cross.character_factors.len()),
            };
            for index in changed {
                if index >= cross.character_factors.len() {
                    continue;
                }
                let factor = cross.character_factors[index];
                let full = &self.编码结果[index].全码;
                let short = &self.编码结果[index].简码;
                if !full_refresh && !full.有变化 && !short.有变化 {
                    continue;
                }
                if !full_refresh {
                    if let Some(previous) = cross.character_codes[index] {
                        if let Some((soft, hard_top)) = cross.targets.get(&previous) {
                            cross.soft -= factor * soft;
                            if index < *hard_top {
                                cross.hard -= 1;
                            }
                        }
                    }
                }
                // If the effective short code differs from the full code, the
                // user never needs the four-key character code, so a word at
                // that four-key position is not a practical collision.
                let code = if short.原始编码 == full.原始编码 {
                    Some(full.原始编码)
                } else {
                    None
                };
                cross.character_codes[index] = code;
                if let Some(code) = code {
                    if let Some((soft, hard_top)) = cross.targets.get(&code) {
                        cross.soft += factor * soft;
                        if index < *hard_top {
                            cross.hard += 1;
                        }
                    }
                }
            }
        }
        if let Some(auxiliary) = &mut self.辅助码缓存 {
            let changed = self.编码器.变化词().map(|indices| indices.to_vec());
            auxiliary.刷新(changed.as_deref(), &self.编码结果, auxiliary.radix);
        }
        let mut 桶序号列表: Vec<_> = self.计数桶列表.iter().map(|_| 0).collect();
        // 开始计算指标
        for 编码信息 in self.编码结果.iter_mut() {
            let 频率 = 编码信息.频率;
            let 桶索引 = if 编码信息.词长 == 1 { 0 } else { 1 };
            let 桶 = &mut self.计数桶列表[桶索引];
            let 桶序号 = 桶序号列表[桶索引];
            let 一二简保护 = 桶索引 == 0
                && 编码信息.简码.原始编码 > 0
                && 编码信息.简码.原始编码 < 参数.进制.pow(3);
            if let Some(缓存) = &mut 桶[0] {
                缓存.处理(桶序号, 频率, &mut 编码信息.全码, 参数, 一二简保护);
            }
            if let Some(缓存) = &mut 桶[1] {
                缓存.处理(桶序号, 频率, &mut 编码信息.简码, 参数, false);
            }
            桶序号列表[桶索引] += 1;
        }

        let mut 目标函数 = 0.0;
        let mut 指标 = 默认指标 {
            characters_full: None,
            words_full: None,
            characters_short: None,
            words_short: None,
            character_word_collision: None,
            auxiliary_two_char: None,
            complexity: None,
        };
        for (桶索引, 桶) in self.计数桶列表.iter().enumerate() {
            let _ = &桶[0].as_ref().map(|x| {
                let (分组指标, 分组目标函数) = x.汇总(参数);
                目标函数 += 分组目标函数;
                if 桶索引 == 0 {
                    指标.characters_full = Some(分组指标);
                } else {
                    指标.words_full = Some(分组指标);
                }
            });
            let _ = &桶[1].as_ref().map(|x| {
                let (分组指标, 分组目标函数) = x.汇总(参数);
                目标函数 += 分组目标函数;
                if 桶索引 == 0 {
                    指标.characters_short = Some(分组指标);
                } else {
                    指标.words_short = Some(分组指标);
                }
            });
        }
        if let Some(cross) = &mut self.字词交叉缓存 {
            指标.character_word_collision = Some(交叉碰撞指标 {
                hard: cross.hard as u64,
                soft: cross.soft,
            });
            目标函数 += cross.soft * cross.weight + cross.hard as f64 * cross.hard_penalty;
        }
        if let Some(auxiliary) = &self.辅助码缓存 {
            指标.auxiliary_two_char = Some(辅助码指标 {
                ambiguous: auxiliary.records.len() as u64,
                first_choice: auxiliary.first_choice,
                weighted_first_choice_rate: if auxiliary.total_weight > 0.0 {
                    auxiliary.first_choice_weight / auxiliary.total_weight
                } else {
                    0.0
                },
                rank_burden: auxiliary.burden,
            });
            目标函数 += auxiliary.burden * auxiliary.weight;
        }
        let 复杂度 = self.计算复杂度(决策);
        指标.complexity = Some(复杂度);
        目标函数 += 参数.正则化强度 * 复杂度;
        (指标, 目标函数)
    }
}
