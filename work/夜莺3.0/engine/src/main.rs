use chai::config::求解器配置;
use chai::contexts::default::默认上下文;
use chai::encoders::default::默认编码器;
use chai::interfaces::command_line::{
    从命令行参数创建, 从目录恢复, 命令, 命令行, 默认命令行参数
};
use chai::objectives::{default::默认目标函数, 目标函数};
use chai::operators::default::默认操作;
use chai::错误;
use clap::Parser;
use std::thread::spawn;

fn main() -> Result<(), 错误> {
    tracing_subscriber::fmt().init();
    let 参数 = 默认命令行参数::parse();

    match 参数.command {
        命令::Server { port } => {
            // 只在 Server 模式下使用异步运行时
            tokio::runtime::Runtime::new().unwrap().block_on(async {
                chai::server::start_server(port).await.unwrap();
            });
        }
        命令::Encode { data } => {
            // 重构参数结构，以便复用现有的数据加载逻辑
            let 重构参数 = 默认命令行参数 {
                command: 命令::Encode { data: data.clone() },
            };
            let 命令行 = 命令行::新建(重构参数, None);
            let 输入 = 从命令行参数创建(&命令行.参数);
            let 上下文 = 默认上下文::新建(输入)?;
            let 编码器 = 默认编码器::新建(&上下文)?;
            let mut 目标函数 = 默认目标函数::新建(&上下文, 编码器)?;
            let (指标, 分数) = 目标函数.计算(&上下文.初始决策, &None);
            let 码表 = 上下文.生成码表(&目标函数.编码结果);
            let 码表路径 = 命令行.输出编码结果(码表);
            let 指标路径 = 命令行.输出指标(&指标, 分数);
            let 配置内容 = serde_yaml::to_string(&上下文.配置).unwrap();
            命令行.输出配置文件(&配置内容);
            print!("分数：{分数:.4e}；{指标}");
            println!("编码结果位于 {码表路径:?}");
            println!("指标位于 {指标路径:?}");
        }
        命令::Optimize {
            data,
            threads,
            resume_from,
        } => {
            let 重构参数 = 默认命令行参数 {
                command: 命令::Optimize {
                    data: data.clone(),
                    threads,
                    resume_from: resume_from.clone(),
                },
            };
            let 命令行 = 命令行::新建(重构参数, None);
            let 输入 = 从命令行参数创建(&命令行.参数);
            let 恢复结果 = if let Some(resume_path) = resume_from {
                println!("从 {:?} 恢复优化进度...", resume_path);
                从目录恢复(&resume_path, threads)?
            } else {
                vec![]
            };
            let _config = 输入.配置.clone();
            let 退火 = match _config.optimization {
                Some(opt) => match opt.metaheuristic {
                    Some(求解器配置::SimulatedAnnealing(sa)) => sa,
                    _ => return Err("配置文件中缺少模拟退火算法配置".into()),
                },
                None => return Err("配置文件中缺少优化配置".into()),
            };
            let mut 线程池 = vec![];
            for 线程序号 in 0..threads {
                let mut 当前线程输入 = 输入.clone();
                let mut 恢复步数 = None;
                if !恢复结果.is_empty() {
                    let mut 恢复配置 = 恢复结果[线程序号].1.clone();
                    // Serialized checkpoints intentionally omit the (large) decision space.
                    // Restore it from the input configuration while retaining the checkpoint's
                    // current mapping; otherwise custom elements cannot be reconstructed and
                    // `--resume-from` fails as soon as an encodable references one of them.
                    恢复配置.form.mapping_space = 当前线程输入.配置.form.mapping_space.clone();
                    恢复配置.generated_mapping_space =
                        当前线程输入.配置.generated_mapping_space.clone();
                    当前线程输入.配置 = 恢复配置;
                    恢复步数 = Some(恢复结果[线程序号].0);
                }
                let 上下文 = 默认上下文::新建(当前线程输入)?;
                let 编码器 = 默认编码器::新建(&上下文)?;
                let mut 目标函数 = 默认目标函数::新建(&上下文, 编码器)?;
                let mut 操作 = 默认操作::按配置新建(&上下文, 退火.search_method)?;
                let 优化方法 = 退火.clone();
                let 子命令行 = 命令行.生成子命令行(线程序号);
                let 子上下文 = 上下文.clone();
                println!(
                    "启动线程 {} 进行优化，日志位于 {}",
                    线程序号,
                    子命令行.输出目录.join("log.txt").display()
                );
                let 返回子命令行 = 子命令行.clone();
                let 未来优化结果 = spawn(move || {
                    let 优化结果 = 优化方法.优化(
                        &子上下文.初始决策,
                        &mut 目标函数,
                        &mut 操作,
                        &子上下文,
                        &子命令行,
                        恢复步数,
                    );
                    let 码表 = 子上下文.生成码表(&目标函数.编码结果);
                    子命令行.输出编码结果(码表);
                    子命令行.输出指标(&优化结果.指标, 优化结果.分数);
                    子命令行.输出配置文件(&优化结果.配置文件);
                    return 优化结果;
                });
                线程池.push((线程序号, 未来优化结果, 返回子命令行));
            }
            let mut 输出结果列表 = vec![];
            for (线程序号, 线程, 子命令行) in 线程池 {
                输出结果列表.push((线程序号, 线程.join().unwrap(), 子命令行));
            }
            输出结果列表.sort_by(|a, b| a.1.分数.partial_cmp(&b.1.分数).unwrap());
            println!();
            println!("优化完成，各线程结果如下：");
            println!();
            for (线程序号, 优化结果, 子命令行) in &输出结果列表 {
                print!(
                    "线程 {} 分数：{:.4e}；{}",
                    线程序号, 优化结果.分数, 优化结果.指标
                );
                println!("配置文件位于 {:?}", 子命令行.输出目录.join("config.yaml"));
                println!("编码结果位于 {:?}", 子命令行.输出目录.join("code.txt"));
                println!("指标位于 {:?}", 子命令行.输出目录.join("metric.txt"));
                println!();
            }
            let 总结目录 = 命令行.输出总结(&输出结果列表);
            println!("全部线程优化结果总结位于 {:?}", 总结目录);
        }
    }
    Ok(())
}
