use super::变异;
use crate::contexts::default::{
    默认上下文, 默认决策, 默认决策变化, 默认决策空间, 默认安排
};
use crate::optimizers::决策;
use crate::错误;
use crate::{元素, 元素图, 棱镜};
use rand::seq::{IndexedRandom, IteratorRandom};
use crate::trial_rng::{random_range, rng};
use serde::{Deserialize, Serialize};
use serde_with::skip_serializing_none;
use std::collections::VecDeque;
use tracing::debug;

pub struct 默认操作 {
    决策空间: 默认决策空间,
    元素图: 元素图,
    棱镜: 棱镜,
    变异配置: 变异配置,
    可交换键: Vec<元素>,
}

#[skip_serializing_none]
#[derive(Debug, Copy, Clone, Serialize, Deserialize)]
pub struct 变异配置 {
    pub random_move: f64,
    pub random_swap: f64,
    pub random_full_key_swap: f64,
}

pub const DEFAULT_MUTATE: 变异配置 = 变异配置 {
    random_move: 0.9,
    random_swap: 0.09,
    random_full_key_swap: 0.01,
};

impl 变异 for 默认操作 {
    type 决策 = 默认决策;
    fn 变异(&mut self, 决策: &mut Self::决策) -> <默认决策 as 决策>::变化 {
        let 总权重 = self.变异配置.random_move
            + self.变异配置.random_swap
            + self.变异配置.random_full_key_swap;
        let 抽样 = crate::trial_rng::random_f64() * 总权重;
        let mut 变化 = if 抽样 < self.变异配置.random_move {
            self.随机移动元素(决策)
        } else if 抽样 < self.变异配置.random_move + self.变异配置.random_swap {
            self.随机交换元素(决策)
        } else {
            self.随机整键交换(决策)
        };
        self.传播(&mut 变化, 决策);
        变化
    }
}

// 默认的问题实现，使用配置文件中的约束来定义各种算子
impl 默认操作 {
    /// 使用默认移动比例创建操作器，保留原有公开 API。
    pub fn 新建(上下文: &默认上下文) -> Result<Self, 错误> {
        Self::按配置新建(上下文, None)
    }

    /// 使用退火配置中的移动比例创建操作器。
    pub fn 按配置新建(
        上下文: &默认上下文,
        变异配置: Option<变异配置>,
    ) -> Result<Self, 错误> {
        let 变异配置 = 变异配置.unwrap_or(DEFAULT_MUTATE);
        let 权重 = [
            变异配置.random_move,
            变异配置.random_swap,
            变异配置.random_full_key_swap,
        ];
        if 权重.iter().any(|x| !x.is_finite() || *x < 0.0) || 权重.iter().sum::<f64>() <= 0.0 {
            return Err("移动方式的权重必须是有限非负数，且总和必须大于 0".into());
        }
        let 可交换键 = 上下文
            .配置
            .form
            .alphabet
            .chars()
            .filter_map(|键| 上下文.棱镜.键转数字.get(&键).map(|x| *x as 元素))
            .collect();
        Ok(Self {
            决策空间: 上下文.决策空间.clone(),
            元素图: 上下文.元素图.clone(),
            棱镜: 上下文.棱镜.clone(),
            变异配置,
            可交换键,
        })
    }

    fn 传播(&self, 变化: &mut <默认决策 as 决策>::变化, 决策: &mut 默认决策) {
        // 初始化队列
        let mut 队列 = VecDeque::new();
        for 元素 in 变化
            .增加元素
            .iter()
            .chain(变化.减少元素.iter())
            .chain(变化.移动元素.iter())
        {
            for 下游元素 in self.元素图.get(元素).unwrap_or(&vec![]) {
                if !队列.contains(下游元素) {
                    队列.push_back(下游元素.clone());
                }
            }
        }
        // 传播直到队列为空
        let mut iters = 0;
        while !队列.is_empty() {
            iters += 1;
            if iters > 100 {
                panic!("传播超过 100 次仍未结束，可能出现死循环");
            }
            let 元素 = 队列.pop_front().unwrap();
            let 当前安排 = 决策.元素[元素];
            let mut 合法 = false;
            let mut 新安排列表 = vec![];
            for 条件安排 in &self.决策空间.元素[元素] {
                if 决策.允许(条件安排) {
                    if 条件安排.安排 == 当前安排 {
                        合法 = true;
                        break;
                    }
                    新安排列表.push(条件安排.安排.clone());
                }
            }
            if !合法 {
                if 新安排列表.is_empty() {
                    panic!("没有合法的安排，传播失败");
                } else {
                    let 新安排 = *新安排列表.choose(&mut rng()).unwrap();
                    if let 默认安排::未选取 = 当前安排 {
                        变化.增加元素.push(元素);
                    } else if let 默认安排::未选取 = 新安排 {
                        变化.减少元素.push(元素);
                    } else {
                        变化.移动元素.push(元素);
                    }
                    决策.元素[元素] = 新安排;
                }
            }
            for 下游元素 in self.元素图.get(&元素).unwrap_or(&vec![]) {
                if !队列.contains(下游元素) {
                    队列.push_back(*下游元素);
                }
            }
        }
    }

    pub fn 随机移动元素(&self, 决策: &mut 默认决策) -> 默认决策变化 {
        let mut rng = rng();
        const MAX_TRIES: usize = 100;
        for _ in 0..MAX_TRIES {
            let 元素 = (0..决策.元素.len()).choose(&mut rng).unwrap();
            let 当前安排 = 决策.元素[元素];
            // 蓄水池抽样
            let mut 下一个安排 = None;
            let mut count = 0;
            for 条件安排 in &self.决策空间.元素[元素] {
                if 条件安排.安排 != 当前安排 && 决策.允许(条件安排) {
                    count += 1;
                    if random_range(0..count) == 0 {
                        下一个安排 = Some(&条件安排.安排);
                    }
                }
            }
            if let Some(下一个安排) = 下一个安排 {
                决策.元素[元素] = *下一个安排;
                debug!(
                    "随机移动元素 {:?} 从 {:?} 到 {:?}",
                    self.棱镜.数字转元素[&元素], 当前安排, 下一个安排
                );
                let mut 增加元素 = vec![];
                let mut 减少元素 = vec![];
                let mut 移动元素 = vec![];
                if let 默认安排::未选取 = 当前安排 {
                    增加元素.push(元素);
                } else if let 默认安排::未选取 = 下一个安排 {
                    减少元素.push(元素);
                } else {
                    移动元素.push(元素);
                }
                return 默认决策变化::新建(增加元素, 减少元素, 移动元素);
            }
        }
        默认决策变化::不变()
    }

    /// 交换两个元素当前的完整安排。只有交换后的两个安排都属于各自的
    /// 决策空间且满足条件时才提交；否则重新抽样。
    pub fn 随机交换元素(&self, 决策: &mut 默认决策) -> 默认决策变化 {
        const MAX_TRIES: usize = 100;
        let 可变元素 = self.棱镜.进制 as usize..决策.元素.len();
        if 可变元素.len() < 2 {
            return 默认决策变化::不变();
        }
        let mut rng = rng();
        for _ in 0..MAX_TRIES {
            let Some(元素一) = 可变元素.clone().choose(&mut rng) else {
                break;
            };
            let Some(元素二) = 可变元素.clone().filter(|x| *x != 元素一).choose(&mut rng)
            else {
                break;
            };
            if 决策.元素[元素一] == 决策.元素[元素二] {
                continue;
            }
            let mut 候选 = 决策.clone();
            候选.元素.swap(元素一, 元素二);
            let 合法 = [元素一, 元素二].iter().all(|元素| {
                self.决策空间.元素[*元素]
                    .iter()
                    .any(|安排| 安排.安排 == 候选.元素[*元素] && 候选.允许(安排))
            });
            if 合法 {
                决策.元素.swap(元素一, 元素二);
                return 默认决策变化::新建(vec![], vec![], vec![元素一, 元素二]);
            }
        }
        默认决策变化::不变()
    }

    /// 把两个编码键在所有直接键位安排中整体互换。
    pub fn 随机整键交换(&self, 决策: &mut 默认决策) -> 默认决策变化 {
        const MAX_TRIES: usize = 100;
        if self.可交换键.len() < 2 {
            return 默认决策变化::不变();
        }
        let mut rng = rng();
        for _ in 0..MAX_TRIES {
            let Some(&键一) = self.可交换键.iter().choose(&mut rng) else {
                break;
            };
            let Some(&键二) = self
                .可交换键
                .iter()
                .filter(|x| **x != 键一)
                .choose(&mut rng)
            else {
                break;
            };
            let mut 候选 = 决策.clone();
            let mut 移动元素 = vec![];
            for 元素 in self.棱镜.进制 as usize..候选.元素.len() {
                let 新安排 = Self::交换安排中的键(候选.元素[元素], 键一, 键二);
                if 新安排 != 候选.元素[元素] {
                    候选.元素[元素] = 新安排;
                    移动元素.push(元素);
                }
            }
            if 移动元素.is_empty() {
                continue;
            }
            let 合法 = 移动元素.iter().all(|元素| {
                self.决策空间.元素[*元素]
                    .iter()
                    .any(|安排| 安排.安排 == 候选.元素[*元素] && 候选.允许(安排))
            });
            if 合法 {
                *决策 = 候选;
                return 默认决策变化::新建(vec![], vec![], 移动元素);
            }
        }
        默认决策变化::不变()
    }

    fn 交换安排中的键(安排: 默认安排, 键一: 元素, 键二: 元素) -> 默认安排 {
        let 默认安排::键位(mut 键位) = 安排 else {
            return 安排;
        };
        for (元素, _) in &mut 键位 {
            if *元素 == 键一 {
                *元素 = 键二;
            } else if *元素 == 键二 {
                *元素 = 键一;
            }
        }
        默认安排::键位(键位)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::contexts::条件安排;
    use rustc_hash::FxHashMap;

    fn 键位(keys: &[元素]) -> 默认安排 {
        let mut result = [(0, 0); 4];
        for (index, key) in keys.iter().enumerate() {
            result[index] = (*key, 0);
        }
        默认安排::键位(result)
    }

    fn 无条件(安排: 默认安排) -> 条件安排<默认安排> {
        条件安排 {
            安排,
            分数: 0.0,
            条件: vec![],
        }
    }

    fn 测试操作(决策空间: 默认决策空间, 可交换键: Vec<元素>) -> 默认操作 {
        默认操作 {
            决策空间,
            元素图: FxHashMap::default(),
            棱镜: 棱镜 {
                键转数字: FxHashMap::default(),
                数字转键: FxHashMap::default(),
                元素转数字: FxHashMap::default(),
                数字转元素: FxHashMap::default(),
                进制: 3,
                可选元素位图索引: FxHashMap::default(),
            },
            变异配置: DEFAULT_MUTATE,
            可交换键,
        }
    }

    #[test]
    fn 随机交换会交换两个合法元素() {
        let a = 键位(&[1]);
        let b = 键位(&[2]);
        let 固定 = vec![无条件(默认安排::未选取)];
        let 空间 = 默认决策空间 {
            元素: vec![
                固定.clone(),
                固定.clone(),
                固定,
                vec![无条件(a), 无条件(b)],
                vec![无条件(a), 无条件(b)],
            ],
        };
        let 操作 = 测试操作(空间, vec![1, 2]);
        let mut 决策 = 默认决策 {
            元素: vec![默认安排::未选取, a, b, a, b],
        };
        let 变化 = 操作.随机交换元素(&mut 决策);
        assert_eq!(决策.元素[3], b);
        assert_eq!(决策.元素[4], a);
        assert_eq!(变化.移动元素.len(), 2);
    }

    #[test]
    fn 整键交换会替换单键和多键安排() {
        let a = 键位(&[1]);
        let b = 键位(&[2]);
        let ab = 键位(&[1, 2]);
        let ba = 键位(&[2, 1]);
        let 固定 = vec![无条件(默认安排::未选取)];
        let 空间 = 默认决策空间 {
            元素: vec![
                固定.clone(),
                固定.clone(),
                固定,
                vec![无条件(a), 无条件(b)],
                vec![无条件(ab), 无条件(ba)],
            ],
        };
        let 操作 = 测试操作(空间, vec![1, 2]);
        let mut 决策 = 默认决策 {
            元素: vec![默认安排::未选取, a, b, a, ab],
        };
        let 变化 = 操作.随机整键交换(&mut 决策);
        assert_eq!(决策.元素[3], b);
        assert_eq!(决策.元素[4], ba);
        assert_eq!(变化.移动元素.len(), 2);
    }

    #[test]
    fn 配置为百分百交换时调度器确实走交换路径() {
        let a = 键位(&[1]);
        let b = 键位(&[2]);
        let 固定 = vec![无条件(默认安排::未选取)];
        let 空间 = 默认决策空间 {
            元素: vec![
                固定.clone(),
                固定.clone(),
                固定,
                vec![无条件(a), 无条件(b)],
                vec![无条件(a), 无条件(b)],
            ],
        };
        let mut 操作 = 测试操作(空间, vec![1, 2]);
        操作.变异配置 = 变异配置 {
            random_move: 0.0,
            random_swap: 1.0,
            random_full_key_swap: 0.0,
        };
        let mut 决策 = 默认决策 {
            元素: vec![默认安排::未选取, a, b, a, b],
        };
        let 变化 = 操作.变异(&mut 决策);
        assert_eq!(决策.元素[3], b);
        assert_eq!(决策.元素[4], a);
        assert_eq!(变化.移动元素.len(), 2);
    }

    #[test]
    fn 交换安排中的键不改变归并和未选取() {
        assert_eq!(
            默认操作::交换安排中的键(默认安排::归并(9), 1, 2),
            默认安排::归并(9)
        );
        assert_eq!(
            默认操作::交换安排中的键(默认安排::未选取, 1, 2),
            默认安排::未选取
        );
    }
}
