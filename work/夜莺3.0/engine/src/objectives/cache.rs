use rustc_hash::FxHashMap;

use super::default::默认目标函数参数;
use super::metric::分组指标;
use super::metric::层级指标;
use super::metric::键长指标;
use super::metric::FingeringMetric;
use super::metric::FingeringMetricUniform;
use super::metric::LevelMetricUniform;
use crate::config::部分权重;
use crate::{最大按键组合长度, 编码, 部分编码信息, 键位分布损失函数};
use std::iter::zip;

#[inline(always)]
fn 加权指法增量(frequency: i64, label: u8) -> i64 {
    frequency * label as i64
}

#[inline(always)]
fn 音型过渡索引(code: 编码, radix: u64, max_index: u64, length: u64) -> Option<usize> {
    (length >= 3).then_some(((code / radix) % max_index) as usize)
}

// 用于缓存计算目标函数的中间结果，方便实现增量计算
#[derive(Debug, Clone)]
pub struct 缓存 {
    partial_weights: 部分权重,
    total_count: usize,
    total_frequency: i64,
    total_pairs: i64,
    total_extended_pairs: i64,
    distribution: Vec<i64>,
    total_pair_equivalence: f64,
    total_phonetic_shape_transition_equivalence: f64,
    total_phonetic_shape_transition_frequency: i64,
    total_extended_pair_equivalence: f64,
    total_duplication: i64,
    total_effective_duplication: i64,
    total_fingering: [i64; 8],
    total_levels: Vec<i64>,
    tiers_duplication: Vec<i64>,
    tiers_duplication_squared: Vec<i64>,
    tiers_effective_duplication: Vec<i64>,
    tiers_effective_duplication_squared: Vec<i64>,
    previous_codes: Vec<编码>,
    previous_duplicates: Vec<u8>,
    previous_protected: Vec<bool>,
    tiers_levels: Vec<Vec<i64>>,
    tiers_fingering: Vec<[i64; 8]>,
    tiers_weighted_fingering: Vec<[i64; 8]>,
    tiers_weighted_pairs: Vec<i64>,
    tiers_phonetic_shape_transition_equivalence: Vec<f64>,
    tiers_phonetic_shape_transition_frequency: Vec<i64>,
    max_index: u64,
    segment: u64,
    length_breakpoints: Vec<u64>,
    radix: u64,
}

impl 缓存 {
    #[inline(always)]
    pub fn 处理(
        &mut self,
        序号: usize,
        频率: u64,
        编码信息: &mut 部分编码信息,
        参数: &默认目标函数参数,
        一二简保护: bool,
    ) {
        let 保护变化 = self.previous_protected[序号] != 一二简保护;
        if !编码信息.有变化 && !保护变化 {
            return;
        }
        编码信息.有变化 = false;
        let 上一个编码 = self.previous_codes[序号];
        if 上一个编码 != 0 {
            self.增减(
                序号,
                频率,
                上一个编码,
                self.previous_duplicates[序号],
                参数,
                -1,
                self.previous_protected[序号],
            );
        }
        self.增减(
            序号,
            频率,
            编码信息.实际编码,
            编码信息.选重标记,
            参数,
            1,
            一二简保护,
        );
        self.previous_codes[序号] = 编码信息.实际编码;
        self.previous_duplicates[序号] = 编码信息.选重标记;
        self.previous_protected[序号] = 一二简保护;
    }

    pub fn 汇总(&self, 参数: &默认目标函数参数) -> (分组指标, f64) {
        let partial_weights = &self.partial_weights;
        let 键位分布信息 = &参数.键位分布信息;
        // 初始化返回值和标量化的损失函数
        let mut 分组指标 = 分组指标 {
            tiers: None,
            key_distribution: None,
            key_distribution_loss: None,
            pair_equivalence: None,
            phonetic_shape_transition_equivalence: None,
            extended_pair_equivalence: None,
            fingering: None,
            duplication: None,
            effective_duplication: None,
            levels: None,
        };
        let mut 损失函数 = 0.0;
        // 一、全局指标
        // 1. 按键分布
        if let Some(key_distribution_weight) = partial_weights.key_distribution {
            // 首先归一化
            let 总频率: i64 = self.distribution.iter().sum();
            let 分布 = self
                .distribution
                .iter()
                .map(|x| *x as f64 / 总频率 as f64)
                .collect();
            let 距离 = 缓存::计算键位分布距离(&分布, 键位分布信息);
            let mut 分布映射 = FxHashMap::default();
            for (i, x) in 分布.iter().enumerate() {
                if let Some(键) = 参数.数字转键.get(&(i as u64)) {
                    分布映射.insert(*键, *x);
                }
            }
            分组指标.key_distribution = Some(分布映射);
            分组指标.key_distribution_loss = Some(距离);
            损失函数 += 距离 * key_distribution_weight;
        }
        // 2. 组合当量
        if let Some(equivalence_weight) = partial_weights.pair_equivalence {
            let equivalence = self.total_pair_equivalence / self.total_pairs as f64;
            分组指标.pair_equivalence = Some(equivalence);
            损失函数 += equivalence * equivalence_weight;
        }
        // 2b. 音码末键到首型键当量
        if let Some(weight) = partial_weights.phonetic_shape_transition_equivalence {
            let equivalence = if self.total_phonetic_shape_transition_frequency > 0 {
                self.total_phonetic_shape_transition_equivalence
                    / self.total_phonetic_shape_transition_frequency as f64
            } else {
                0.0
            };
            分组指标.phonetic_shape_transition_equivalence = Some(equivalence);
            损失函数 += equivalence * weight;
        }
        // 3. 词间当量
        if let Some(equivalence_weight) = partial_weights.extended_pair_equivalence {
            let equivalence =
                self.total_extended_pair_equivalence / self.total_extended_pairs as f64;
            分组指标.extended_pair_equivalence = Some(equivalence);
            损失函数 += equivalence * equivalence_weight;
        }
        // 4. 差指法
        if let Some(fingering_weight) = &partial_weights.fingering {
            let mut fingering = FingeringMetric::default();
            for (i, weight) in fingering_weight.iter().enumerate() {
                if let Some(weight) = weight {
                    fingering[i] = Some(self.total_fingering[i] as f64 / self.total_pairs as f64);
                    损失函数 += self.total_fingering[i] as f64 * weight;
                }
            }
            分组指标.fingering = Some(fingering);
        }
        // 5. 重码
        if let Some(duplication_weight) = partial_weights.duplication {
            let duplication = self.total_duplication as f64 / self.total_frequency as f64;
            分组指标.duplication = Some(duplication);
            损失函数 += duplication * duplication_weight;
        }
        if let Some(weight) = partial_weights.effective_duplication {
            let value = self.total_effective_duplication as f64 / self.total_frequency as f64;
            分组指标.effective_duplication = Some(value);
            损失函数 += value * weight;
        }
        // 6. 简码
        if let Some(levels_weight) = &partial_weights.levels {
            let mut levels: Vec<键长指标> = Vec::new();
            for (ilevel, level) in levels_weight.iter().enumerate() {
                let value = self.total_levels[ilevel] as f64 / self.total_frequency as f64;
                损失函数 += value * level.frequency;
                levels.push(键长指标 {
                    length: level.length,
                    frequency: value,
                });
            }
            分组指标.levels = Some(levels);
        }
        // 二、分级指标
        if let Some(tiers_weight) = &partial_weights.tiers {
            let mut tiers: Vec<层级指标> = tiers_weight
                .iter()
                .map(|x| 层级指标 {
                    top: x.top,
                    duplication: None,
                    duplication_squared: None,
                    effective_duplication: None,
                    effective_duplication_squared: None,
                    levels: None,
                    fingering: None,
                    weighted_fingering: None,
                    phonetic_shape_transition_equivalence: None,
                })
                .collect();
            for (itier, tier_weights) in tiers_weight.iter().enumerate() {
                let count = tier_weights.top.unwrap_or(self.total_count) as f64;
                // 1. 重码
                if let Some(duplication_weight) = tier_weights.duplication {
                    let duplication = self.tiers_duplication[itier];
                    损失函数 += duplication as f64 / count * duplication_weight;
                    tiers[itier].duplication = Some(duplication as u64);
                }
                // 1b. 选重平方
                if let Some(duplication_squared_weight) = tier_weights.duplication_squared {
                    let duplication_squared = self.tiers_duplication_squared[itier];
                    损失函数 += duplication_squared as f64 / count * duplication_squared_weight;
                    tiers[itier].duplication_squared = Some(duplication_squared as u64);
                }
                if let Some(weight) = tier_weights.effective_duplication {
                    let value = self.tiers_effective_duplication[itier];
                    损失函数 += value as f64 / count * weight;
                    tiers[itier].effective_duplication = Some(value as u64);
                }
                if let Some(weight) = tier_weights.effective_duplication_squared {
                    let value = self.tiers_effective_duplication_squared[itier];
                    损失函数 += value as f64 / count * weight;
                    tiers[itier].effective_duplication_squared = Some(value as u64);
                }
                // 2. 简码
                if let Some(level_weight) = &tier_weights.levels {
                    for (ilevel, level) in level_weight.iter().enumerate() {
                        损失函数 +=
                            self.tiers_levels[itier][ilevel] as f64 / count * level.frequency;
                    }
                    tiers[itier].levels = Some(
                        level_weight
                            .iter()
                            .enumerate()
                            .map(|(i, v)| LevelMetricUniform {
                                length: v.length,
                                frequency: self.tiers_levels[itier][i] as u64,
                            })
                            .collect(),
                    );
                }
                // 3. 差指法
                if let Some(fingering_weight) = &tier_weights.fingering {
                    let mut fingering = FingeringMetricUniform::default();
                    for (i, weight) in fingering_weight.iter().enumerate() {
                        if let Some(weight) = weight {
                            let value = self.tiers_fingering[itier][i];
                            fingering[i] = Some(value as u64);
                            损失函数 += value as f64 / count * weight;
                        }
                    }
                    tiers[itier].fingering = Some(fingering);
                }
                // 4. 字频加权差指法
                if let Some(fingering_weight) = &tier_weights.weighted_fingering {
                    let mut fingering = FingeringMetric::default();
                    let pairs = self.tiers_weighted_pairs[itier] as f64;
                    for (i, weight) in fingering_weight.iter().enumerate() {
                        if let Some(weight) = weight {
                            let value = if pairs > 0.0 {
                                self.tiers_weighted_fingering[itier][i] as f64 / pairs
                            } else {
                                0.0
                            };
                            fingering[i] = Some(value);
                            损失函数 += value * weight;
                        }
                    }
                    tiers[itier].weighted_fingering = Some(fingering);
                }
                // 5. 分层音型过渡当量
                if let Some(weight) = tier_weights.phonetic_shape_transition_equivalence {
                    let frequency = self.tiers_phonetic_shape_transition_frequency[itier];
                    let equivalence = if frequency > 0 {
                        self.tiers_phonetic_shape_transition_equivalence[itier] / frequency as f64
                    } else {
                        0.0
                    };
                    tiers[itier].phonetic_shape_transition_equivalence = Some(equivalence);
                    损失函数 += equivalence * weight;
                }
            }
            分组指标.tiers = Some(tiers);
        }
        (分组指标, 损失函数)
    }
}

impl 缓存 {
    pub fn new(
        partial_weights: &部分权重, radix: u64, total_count: usize, max_index: u64
    ) -> Self {
        let total_frequency = 0;
        let total_pairs = 0;
        let total_extended_pairs = 0;
        // 初始化全局指标的变量
        // 1. 只有加权指标，没有计数指标
        let distribution = vec![0; radix as usize];
        let total_pair_equivalence = 0.0;
        let total_phonetic_shape_transition_equivalence = 0.0;
        let total_phonetic_shape_transition_frequency = 0;
        let total_extended_pair_equivalence = 0.0;
        // 2. 有加权指标，也有计数指标
        let total_duplication = 0;
        let total_effective_duplication = 0;
        let total_fingering = [0; 8];
        let nlevel = partial_weights.levels.as_ref().map_or(0, |v| v.len());
        let total_levels = vec![0; nlevel];
        // 初始化分级指标的变量
        let ntier = partial_weights.tiers.as_ref().map_or(0, |v| v.len());
        let tiers_duplication = vec![0; ntier];
        let tiers_duplication_squared = vec![0; ntier];
        let tiers_effective_duplication = vec![0; ntier];
        let tiers_effective_duplication_squared = vec![0; ntier];
        let mut tiers_levels = vec![];
        if let Some(tiers) = &partial_weights.tiers {
            for tier in tiers {
                let vec = vec![0; tier.levels.as_ref().map_or(0, |v| v.len())];
                tiers_levels.push(vec);
            }
        }
        let tiers_fingering = vec![[0; 8]; ntier];
        let tiers_weighted_fingering = vec![[0; 8]; ntier];
        let tiers_weighted_pairs = vec![0; ntier];
        let tiers_phonetic_shape_transition_equivalence = vec![0.0; ntier];
        let tiers_phonetic_shape_transition_frequency = vec![0; ntier];
        let segment = radix.pow((最大按键组合长度 - 1) as u32);
        let length_breakpoints: Vec<u64> = (0..=8).map(|x| radix.pow(x)).collect();

        Self {
            partial_weights: partial_weights.clone(),
            total_count,
            total_frequency,
            total_pairs,
            total_extended_pairs,
            distribution,
            total_pair_equivalence,
            total_phonetic_shape_transition_equivalence,
            total_phonetic_shape_transition_frequency,
            total_extended_pair_equivalence,
            total_duplication,
            total_effective_duplication,
            total_fingering,
            total_levels,
            tiers_duplication,
            tiers_duplication_squared,
            tiers_effective_duplication,
            tiers_effective_duplication_squared,
            previous_codes: vec![0; total_count],
            previous_duplicates: vec![0; total_count],
            previous_protected: vec![false; total_count],
            tiers_levels,
            tiers_fingering,
            tiers_weighted_fingering,
            tiers_weighted_pairs,
            tiers_phonetic_shape_transition_equivalence,
            tiers_phonetic_shape_transition_frequency,
            max_index,
            segment,
            length_breakpoints,
            radix,
        }
    }

    /// 用指分布偏差
    /// 计算按键使用率与理想使用率之间的偏差。对于每个按键，偏差是实际频率与理想频率之间的差值乘以一个惩罚系数。用户可以根据自己的喜好自定义理想频率和惩罚系数。
    fn 计算键位分布距离(
        distribution: &Vec<f64>,
        ideal_distribution: &Vec<键位分布损失函数>,
    ) -> f64 {
        let mut distance = 0.0;
        for (frequency, loss) in zip(distribution, ideal_distribution) {
            let diff = frequency - loss.理想值;
            if diff > 0.0 {
                distance += loss.高于惩罚 * diff;
            } else {
                distance -= loss.低于惩罚 * diff;
            }
        }
        distance
    }

    #[inline(always)]
    pub fn 增减(
        &mut self,
        index: usize,
        frequency: u64,
        code: 编码,
        duplicate: u8,
        parameters: &默认目标函数参数,
        sign: i64,
        一二简保护: bool,
    ) {
        let frequency = frequency as i64 * sign;
        let radix = self.radix;
        let length = self
            .length_breakpoints
            .iter()
            .position(|&x| code < x)
            .unwrap() as u64;
        self.total_frequency += frequency;
        self.total_pairs += (length - 1) as i64 * frequency;
        let partial_weights = &self.partial_weights;
        // 一、全局指标
        // 1. 按键分布
        if partial_weights.key_distribution.is_some() {
            let mut current = code;
            while current > 0 {
                let key = current % self.radix;
                if let Some(x) = self.distribution.get_mut(key as usize) {
                    *x += frequency;
                }
                current /= self.radix;
            }
        }
        // 2. 组合当量
        if partial_weights.pair_equivalence.is_some() {
            let mut code = code;
            while code > self.radix {
                let partial_code = (code % self.max_index) as usize;
                self.total_pair_equivalence += parameters.当量信息[partial_code] * frequency as f64;
                code /= self.segment;
            }
        }
        // 2b. 只取第二键到第三键；前两键是固定双拼，第三键是首型。
        if let (Some(_), Some(transition)) = (
            partial_weights.phonetic_shape_transition_equivalence,
            音型过渡索引(code, radix, self.max_index, length),
        ) {
            self.total_phonetic_shape_transition_equivalence +=
                parameters.transition_equivalence[transition] * frequency as f64;
            self.total_phonetic_shape_transition_frequency += frequency;
        }
        // 4. 差指法
        if let Some(fingering) = &partial_weights.fingering {
            let mut code = code;
            while code > radix {
                let label = parameters.指法计数[(code % self.max_index) as usize];
                for (i, weight) in fingering.iter().enumerate() {
                    if weight.is_some() {
                        self.total_fingering[i] += frequency * label[i] as i64;
                    }
                }
                code /= self.segment;
            }
        }
        // 5. 重码
        if duplicate > 0 {
            self.total_duplication += frequency;
            if !一二简保护 {
                self.total_effective_duplication += frequency;
            }
        }
        // 6. 简码
        if let Some(levels) = &partial_weights.levels {
            for (ilevel, level) in levels.iter().enumerate() {
                if level.length == length as usize {
                    self.total_levels[ilevel] += frequency;
                }
            }
        }
        // 二、分级指标
        if let Some(tiers) = &partial_weights.tiers {
            for (itier, tier) in tiers.iter().enumerate() {
                if index >= tier.top.unwrap_or(self.total_count) {
                    continue;
                }
                // 1. 重码
                if duplicate > 0 {
                    self.tiers_duplication[itier] += sign;
                    self.tiers_duplication_squared[itier] += sign * (2 * duplicate as i64 - 1);
                    if !一二简保护 {
                        self.tiers_effective_duplication[itier] += sign;
                        self.tiers_effective_duplication_squared[itier] +=
                            sign * (2 * duplicate as i64 - 1);
                    }
                }
                // 2. 简码
                if let Some(levels) = &tier.levels {
                    for (ilevel, level) in levels.iter().enumerate() {
                        if level.length == length as usize {
                            self.tiers_levels[itier][ilevel] += sign;
                        }
                    }
                }
                // 3. 差指法
                if let Some(fingering) = &tier.fingering {
                    let mut code = code;
                    while code > radix {
                        let label = parameters.指法计数[(code % self.max_index) as usize];
                        for (i, weight) in fingering.iter().enumerate() {
                            if weight.is_some() {
                                self.tiers_fingering[itier][i] += sign * label[i] as i64;
                            }
                        }
                        code /= self.segment;
                    }
                }
                // 4. 字频加权差指法
                if let Some(fingering) = &tier.weighted_fingering {
                    self.tiers_weighted_pairs[itier] += (length - 1) as i64 * frequency;
                    let mut code = code;
                    while code > radix {
                        let label = parameters.指法计数[(code % self.max_index) as usize];
                        for (i, weight) in fingering.iter().enumerate() {
                            if weight.is_some() {
                                self.tiers_weighted_fingering[itier][i] +=
                                    加权指法增量(frequency, label[i]);
                            }
                        }
                        code /= self.segment;
                    }
                }
                // 5. 分层音型过渡当量
                if let (Some(_), Some(transition)) = (
                    tier.phonetic_shape_transition_equivalence,
                    音型过渡索引(code, radix, self.max_index, length),
                ) {
                    self.tiers_phonetic_shape_transition_equivalence[itier] +=
                        parameters.transition_equivalence[transition] * frequency as f64;
                    self.tiers_phonetic_shape_transition_frequency[itier] += frequency;
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{加权指法增量, 缓存, 音型过渡索引};
    use crate::config::{层级权重, 部分权重};
    use crate::objectives::default::默认目标函数参数;
    use crate::部分编码信息;
    use rustc_hash::FxHashMap;

    #[test]
    fn 分层加权指法对高低频对象保持十比一梯度() {
        let 低频贡献 = 加权指法增量(10, 1);
        let 高频贡献 = 加权指法增量(100, 1);
        assert_eq!(高频贡献, 低频贡献 * 10);
        assert_eq!(加权指法增量(-100, 1), -高频贡献);
    }

    #[test]
    fn 音型过渡只取第二键到第三键() {
        let radix = 30;
        let max_index = radix * radix;
        // little-endian编码：b=2, c=3, z=26, k=11。
        let bcz = 2 + 3 * radix + 26 * radix * radix;
        let bck = 2 + 3 * radix + 11 * radix * radix;
        assert_eq!(
            音型过渡索引(bcz, radix, max_index, 3),
            Some((3 + 26 * radix) as usize)
        );
        assert_eq!(
            音型过渡索引(bck, radix, max_index, 3),
            Some((3 + 11 * radix) as usize)
        );
        assert_eq!(音型过渡索引(2 + 3 * radix, radix, max_index, 2), None);
    }

    #[test]
    fn 一二简保护会从有效全码重码中移除该字() {
        let tier = 层级权重 {
            top: Some(1),
            duplication: None,
            duplication_squared: None,
            effective_duplication: Some(1.0),
            effective_duplication_squared: Some(1.0),
            levels: None,
            fingering: None,
            weighted_fingering: None,
            phonetic_shape_transition_equivalence: None,
        };
        let weights = 部分权重 {
            tiers: Some(vec![tier]),
            duplication: None,
            effective_duplication: Some(1.0),
            key_distribution: None,
            pair_equivalence: None,
            phonetic_shape_transition_equivalence: None,
            extended_pair_equivalence: None,
            fingering: None,
            levels: None,
        };
        let parameters = 默认目标函数参数 {
            键位分布信息: vec![],
            当量信息: vec![],
            transition_equivalence: vec![],
            指法计数: vec![],
            数字转键: FxHashMap::default(),
            正则化强度: 0.0,
            进制: 27,
        };
        let mut cache = 缓存::new(&weights, 27, 1, 1);
        let mut code = 部分编码信息 {
            实际编码: 1,
            选重标记: 1,
            有变化: true,
            ..Default::default()
        };
        cache.处理(0, 100, &mut code, &parameters, true);
        let (protected, _) = cache.汇总(&parameters);
        assert_eq!(protected.effective_duplication, Some(0.0));
        assert_eq!(
            protected.tiers.as_ref().unwrap()[0].effective_duplication,
            Some(0)
        );

        // 全码没有变化，仅简码保护消失，也必须刷新有效重码缓存。
        cache.处理(0, 100, &mut code, &parameters, false);
        let (unprotected, _) = cache.汇总(&parameters);
        assert_eq!(unprotected.effective_duplication, Some(1.0));
        assert_eq!(
            unprotected.tiers.as_ref().unwrap()[0].effective_duplication,
            Some(1)
        );
    }
}
