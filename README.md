# ZJUT LUG · Linux 新手村

**三个小游戏**，不是答题：

1. **系统识别**：看桌面画面，在倒计时内分进 Linux / Windows。
2. **命令行猜词**：看中文任务，把命令块按顺序拼进终端。
3. **发行版盲盒**：目标 Logo 在 4 个盲盒里短暂出现，盒子关上后选中它。

不收学号、不联网、不写数据库。三关走完会得到一张终端里的**新手村毕业画面**，可以拍照。

## 运行

需要 [uv](https://docs.astral.sh/uv/)。活动前联网跑一次，现场离线可玩：

```bash
cd lug-village
mise exec -- uv sync
./lug
```

终端至少 **80 x 24**，推荐 **100 x 30** 全屏。窗口变化会自动重排。

调试时固定随机种子：

```bash
./lug --seed 7
```

## 操作

| 键 / 鼠标 | 作用 |
| --- | --- |
| `Tab` / `←` `→` | 菜单切换按钮 |
| `Enter` / `空格` | 确认、开始、执行、开盒 |
| `←` / `→` 或 `A` / `D` | 系统识别：分拣桌面 |
| `方向键` | 命令行猜词：选词块；发行版盲盒：选盒子 |
| `空格` | 拼命令时加入词块 |
| `Backspace` | 拼命令时删除最后一个词块 |
| `鼠标左键` | 点按钮、点词块、点盲盒、点分拣按钮 |
| `P` / `Esc` | 游戏中暂停 |
| `Ctrl-C` | 退出 |

暂停菜单支持 `继续 / 重开 / 退出`，也可以用鼠标点。

## 三个小游戏

### 1. 系统识别

- 10 张桌面画面，每张 6 秒
- 按 `←` 判 Linux，按 `→` 判 Windows；也可以点底部按钮
- 正确加分、连击；错误或超时掉 1 条命
- 3 条命用完失败
- 桌面素材是本地生成/保存的 PNG，用真彩半块字符画在终端里

### 2. 命令行猜词

- 6 个任务，每个 12 秒
- 中文任务示例：「列出所有文件（含隐藏）」「把 a.txt 复制为 b.txt」「搜索 TODO」
- 用方向键选词块，空格加入，Backspace 删除，Enter 执行
- 词块里混有干扰项，必须拼出完整且顺序正确的命令
- 错了或超时掉 1 条命，可以重试同一个任务；3 条命用完失败
- 任务包括 `ls -la`、`cd ..`、`pwd`、`mkdir demo`、`cp`、`rm`、`grep`、`cat`

### 3. 发行版盲盒

- 8 轮，3 条命
- 每轮给出一个目标发行版（Ubuntu / Debian / Arch Linux / Fedora / Linux Mint / openSUSE）
- 4 个盲盒会打开 1.35 秒，展示里面的 Logo，然后全部关上
- 在 4.5 秒内选中刚才出现目标 Logo 的盒子
- 选中正确加分；错误或超时掉 1 条命
- Logo 用真彩半块字符绘制，不依赖终端图片协议

## 终端特性

- 真彩 TUI，30 FPS 主循环
- 标题页自动选择图片协议显示 Tux：
  - Kitty / Ghostty：Kitty 图形协议
  - WezTerm：iTerm2 内联图片（`OSC 1337`）
  - Tabby：Sixel
  - 其他 / ConPTY：半块字符兜底
- SGR 鼠标（`1000` / `1006`）
- 方向键、Tab、鼠标、`WASD` 都可用
- 窗口缩放自动重排

## 项目结构

```text
lug             启动脚本
main.py         状态机、输入、30 FPS 主循环
village.py      三关流程、成绩、毕业判定
ui.py           标题 / 说明 / 关卡介绍 / 结果 / 暂停 / 毕业
sort_game.py    系统识别
command_game.py 命令行猜词
box_game.py     发行版盲盒
canvas.py       真彩画布
term.py         终端输入、图片协议、SGR 鼠标
assetslib.py    PNG / 半块降采样
assets/         Tux、发行版 Logo、桌面截图
tools/          素材与 Sixel 调色板生成脚本
```

## 测试

```bash
mise exec -- uv run python -m py_compile main.py ui.py village.py sort_game.py command_game.py box_game.py canvas.py term.py assetslib.py
```

已验证：

- 80x24 / 100x30 布局
- 三关完整流程、暂停、结果、毕业
- 系统识别：键盘 / 鼠标分拣、超时、掉命、通关
- 命令行猜词：词块选择、删除、执行、错误重试、通关
- 发行版盲盒：观察 / 关上 / 选择、正确与错误、通关
- WezTerm（iTerm2）、Tabby（Sixel）、ConPTY（半块）三种图片链路无 Traceback
