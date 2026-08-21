# libchai 汉字编码输入方案优化算法

`libchai` 是使用 Rust 实现的汉字编码输入方案的优化算法。它同时发布为一个 Rust crate 和一个 NPM 模块，前者可以在 Rust 项目中安装为依赖来使用，后者可以通过汉字自动拆分系统的图形界面来使用。

`chai` 是使用 `libchai` 实现的命令行程序，用户提供方案的配置文件、词信息文件等，本程序能够生成编码并评测一系列指标，以及基于退火算法优化元素的布局。

## 使用 `chai`

在[发布页面](https://github.com/hanzi-chai/libchai/releases)根据您的操作系统下载相应的压缩包，支持 Windows, macOS, Linux (GNU), Linux (musl) 等多种不同的环境。压缩包中有以下的示例文件：

- `examples/米十五笔.yaml`: 配置文件示例，具体的格式解释参见 [config.yaml 详解](https://docs.chaifen.app/docs/tutorial/config)；这个文件也可以由[汉字自动拆分系统](https://chaifen.app/)生成；
- `examples/米十五笔.txt`: 词信息文件示例，每个字一行，每行的内容依次为汉字、空格分隔的汉字拆分序列；这个文件也可由自动拆分系统生成；
- `assets/distribution.txt`：用指分布文件示例，每个按键一行，每行的内容为以制表符分隔的按键、目标频率、低频率惩罚系数、高频率惩罚系数；
- `assets/equivalence.txt`：双键速度当量文件示例，每个按键组合一行，每行的内容为以制表符分隔的按键组合和当量；

`chai` 支持三个不同的命令：`encode`、`optimize` 和 `server`，各个命令的详细介绍如下：

### 编码并计算指标

`encode` 命令使用方案文件和拆分表计算出字词编码并统计各类评测指标。例如，您可以运行

```bash
./chai encode examples/米十五笔.yaml -e examples/米十五笔.txt
```

完整介绍如下：

```bash
> ./chai encode -h
使用方案文件和拆分表计算出字词编码并统计各类指标

Usage: chai encode [OPTIONS] [CONFIG]

Arguments:
  [CONFIG]  方案文件，默认为 config.yaml

Options:
  -e, --encodables <FILE>        频率序列表，默认为 elements.txt
  -k, --key-distribution <FILE>  单键用指分布表，默认为 assets 目录下的 distribution.txt
  -p, --pair-equivalence <FILE>  双键速度当量表，默认为 assets 目录下的 equivalence.txt
```

### 优化

`optimize` 命令基于拆分表和方案文件中的配置优化元素布局。例如，您可以运行

```bash
./chai optimize examples/米十五笔.yaml -e examples/米十五笔.txt -t 4
```

完整介绍如下：

```bash
> ./chai optimize -h
基于配置文件优化决策

Usage: chai optimize [OPTIONS] [CONFIG]

Arguments:
  [CONFIG]  方案文件，默认为 config.yaml

Options:
  -e, --encodables <FILE>          频率序列表，默认为 elements.txt
  -k, --key-distribution <FILE>    单键用指分布表，默认为 assets 目录下的 distribution.txt
  -p, --pair-equivalence <FILE>    双键速度当量表，默认为 assets 目录下的 equivalence.txt
  -t, --threads <THREADS>          优化时使用的线程数 [default: 1]
  -r, --resume-from <RESUME_FROM>  是否要从某个输出目录恢复 如果指定了这个参数，程序会在该目录寻找 checkpoint-*.yaml 来恢复优化进度
```

在优化过程中，您可以随时停止优化并关闭终端，断点数据会保存在相应的文件夹中。若希望下一次计算从此前的某个断点继续，则需要加上 `-r` 参数。例如，上一次计算的结果在 `output-02-20+20_26_36` 中，则可以加上 `-r output-02-20+20_26_36`。值得注意的是，使用的线程数量需要和此前一致，否则无法将所有断点文件均继续计算。

### 启动服务器

`server` 命令​启动 Web 服务。例如，您可以运行

```bash
./chai server -p 12345
```

完整介绍如下：

```bash
> ./chai server -h
启动 HTTP API 服务器

Usage: chai server [OPTIONS]

Options:
  -p, --port <PORT>  服务器端口号 [default: 3200]
```

## 使用 `libchai`

若命令行程序的功能不能满足您的要求，您可以通过编程的方式直接使用 `libchai`。首先在本地配置好 Rust 环境，然后将 `libchai` 安装为依赖。您可以参照 [`libchai-smdc`](https://github.com/hanzi-chai/libchai-smdc) 项目来进一步了解如何通过二次开发来实现个性化的编码、评测、优化逻辑。

## 开发

需要首先运行 `fetch` 脚本下载相关数据资源。然后 `cargo run` 即可编译运行。

您也可以运行 `cargo bench` 来运行性能测试。
