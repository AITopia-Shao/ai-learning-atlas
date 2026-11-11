"""Build the offline graph from curated curriculum structure and existing sources.
Run from any directory: python graph/build_graph.py
"""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent.parent
NODES, EDGES, INDEX = [], [], {}
DOCS = {p.name: p.read_text(encoding='utf-8-sig') for p in sorted(ROOT.glob('*.md')) if re.match(r'(0[1-9]|10)_', p.name)}
URLS = {}
for filename, body in DOCS.items():
    for label, url in re.findall(r'\[([^\]]+)\]\((https?://[^\s)]+)\)', body):
        item = URLS.setdefault(url, {'labels': [], 'docs': []})
        if label not in item['labels']: item['labels'].append(label)
        if filename not in item['docs']: item['docs'].append(filename)
VERSIONS = json.loads((ROOT / 'cs336_2025_versions.json').read_text(encoding='utf-8-sig'))
for a in VERSIONS['assignments']:
    for label, url in [(f"A{a['assignment']} 固定代码", a['tree_url']), (f"A{a['assignment']} README", a['readme_url'])] + [(h['name'], h['url']) for h in a['handouts']]:
        URLS.setdefault(url, {'labels': [label], 'docs': ['06_语言模型与综合实践.md']})

def node(id, label, kind, parent=None, **kw):
    assert id not in INDEX, id
    n = dict(id=id, label=label, type=kind, **kw)
    if parent:
        n['parent'] = parent
        n.setdefault('domain', INDEX[parent].get('domain', parent))
        n.setdefault('doc', INDEX[parent].get('doc', ''))
        n.setdefault('priority', INDEX[parent].get('priority', '核心'))
        edge(parent, id, 'contains', '包含', '课程结构与主题划分来自本地学习路线。')
    NODES.append(n); INDEX[id] = n
    return id

def edge(source, target, kind, label, reason):
    if not any(e['source'] == source and e['target'] == target and e['type'] == kind for e in EDGES):
        EDGES.append(dict(source=source, target=target, type=kind, label=label, reason=reason))

def domain(id, label, color, desc):
    node(id, label, 'domain', domain=id, color=color, description=desc)

for args in [
 ('math','数学基础','#8aa8ff','线性代数、微积分、概率、统计与优化；和编程并行起步。'),
 ('code','编程与实验','#6ecdb1','Python → 抽象与算法 → 科学计算 → 独立训练工程。'),
 ('systems','计算机系统','#f3b978','C、内存层次、OS、网络与 GPU；在 CS336 A2 前汇入。'),
 ('ml','机器学习','#c7a2ed','入门建模、统计实验与数学推导；不要求重复全修三门入门课。'),
 ('ai','通识人工智能','#e9c96b','搜索、推理、规划与决策。可与机器学习入门并行。'),
 ('dl','深度学习','#6bcadd','D2L 是共同实现基础，之后分叉至视觉、语言与深度强化学习。'),
 ('cv','计算机视觉','#ed9da9','CS231n 专项；完整视觉课不是语言模型方向的硬先修。'),
 ('nlp','自然语言处理','#88c88c','CS224n 语言任务、Transformer 与 Hugging Face 工程补充。'),
 ('rl','强化学习','#ce9bd3','赵世钰 → 王树森 → R1–R5 实验；策略梯度连接 LLM 后训练。'),
 ('lm','语言模型','#f3a17e','CS336 五项作业按能力分阶段进入，最后形成完整小模型实验。'),
]: domain(*args)

def course(id, label, dom, doc, description, topics, priority='核心', edition=''):
    filename = next(k for k in DOCS if k.startswith(doc+'_'))
    node(id,label,'course',dom,doc=filename,description=description,priority=priority,edition=edition)
    for key, title, detail in topics:
        node(id+'.'+key,title,'topic',id,description=detail)

def T(spec):
    return [tuple(row.split('|',2)) for row in spec.strip().split('\n')]

course('la','MIT 18.06SC · 线性代数','math','01','Strang 主线。每讲习题，单元考试与 Final；投影、谱与 SVD 不跳。',T('''space|线性方程与子空间|消元、LU、秩、基与四个基本子空间；解释解的存在性与唯一性。
projection|正交、投影与最小二乘|推导正规方程，理解 QR；用 NumPy lstsq 验证，避免把显式求逆当默认方法。
eigen|特征值与二次型|对角化、对称矩阵、正定性；用二次型解释曲率。
svd|SVD 与低秩逼近|奇异值、伪逆、压缩；连接 PCA 与低秩参数化。'''),edition='Fall 2011 Scholar；2010 版补充')
course('calc1','MIT 18.01SC · 单变量微积分','math','01','按五单元学习，做配套题与考试；复杂积分技巧可按方向降优先级。',T('''diff|微分与链式法则|极限、连续、指数与对数求导；推导 sigmoid 导数。
extrema|微分应用与极值|驻点、曲率、Newton 方法；用一元函数检查梯度下降步长。
integral|定积分与积分技巧|计算归一化常数与期望；复杂弧长等不作为 AI 统一门槛。
taylor|无穷与 Taylor 展开|一阶、二阶近似；比较解析导数与数值差分。'''),edition='Fall 2010 Scholar')
course('calc2','MIT 18.02SC · 多变量微积分','math','01','偏导和梯度核心必学；积分与换元基础保留，向量场定理按方向选读。',T('''vectors|Unit 1 · 向量与矩阵|向量几何、矩阵与参数曲线；线代已熟可复习。
grad|Unit 2 · 偏导与梯度|全微分、方向导数、向量链式法则、约束极值与 Lagrange 乘子。
integrals|Units 3–4 · 多重积分|联合密度、二重/三重积分、换元与 Jacobian 行列式。
fields|向量场专题 · 选读|线积分、Green、Stokes、通量与散度；并非 ML 统一前置。'''),edition='Fall 2010 Scholar')
course('prob','MIT RES.6-012 + 6.041SC','math','01','RES.6-012 学讲解，6.041SC 做 recitation、问题集和考试；按主题而非视频编号匹配。',T('''bayes|L1–4 · 条件概率与 Bayes|概率模型、计数、条件概率、独立性；区分条件独立与独立。
discrete|L5–7 · 离散随机变量|PMF、期望、方差、联合与条件分布。
continuous|L8–12 · 连续与多元变量|PDF/CDF、变量变换、协方差、全期望。
markov|L13–18 · 随机过程|Bernoulli/Poisson 过程与 Markov 链；Markov 链在 RL 前补齐。
limit|L19–25 · 极限定理与推断|LLN、CLT、Bayesian 与经典推断；用模拟考察样本均值。'''),edition='2018 视频 + 2013 习题')
course('stats','MIT 18.05 · 统计推断选读','math','01','按缺口学习统计部分，无需重复概率。部分原课练习使用 R。',T('''mle|似然、MLE 与 Bayesian 更新|从数据写似然；区分 MLE、先验和后验。
interval|区间估计与 bootstrap|偏差、方差与不确定性；正确解释置信区间。
test|假设检验与回归不确定性|p 值、效果大小、回归估计的不确定性。'''),edition='Spring 2022 · 核心选读')
course('mml','MML · 数学桥接','math','01','用作者免费书稿补矩阵微积分与优化；信息论结合 D2L/NLP 学习。',T('''matrix|Ch.5 · 向量与矩阵微积分|Jacobian、Hessian、链式法则、形状检查；推导 softmax 交叉熵。
distribution|Ch.6 · 概率与分布|将概率概念接回建模；结合统计课程补 MLE/MAP。
opt|Ch.7 · 连续优化|GD/SGD、正则化、约束；比较不同学习率收敛轨迹。
info|补充 · 熵、交叉熵与 KL|结合 D2L/CS224n 的损失函数理解，不另设完整信息论先修课。'''))
course('convex','Boyd · 凸优化选读','math','01','研究深化；无需在进入 D2L 前完整读完。',T('''convexity|Ch.2–4 · 凸集、凸函数与问题|认识凸性、局部/全局最优与问题形式。
dual|Ch.5 · 对偶概念|约束、乘子、对偶；连接 SVM 与策略约束。
descent|Ch.9 · 无约束优化|下降方法；完整证明与内点法按研究方向深化。'''),priority='选修')
course('python','Harvard CS50P · Python','code','02','完成 Psets 0–8 与 Final Project；官方提交及认证需依课程账户规则。',T('''basics|函数、条件与循环|变量、函数、作用域、条件、循环；Week 0 开始。
structure|异常、库与面向对象|模块、可变对象、类与迭代；能读懂异常堆栈。
tests|测试、文件与正则|边界测试、文件读写、正则；调试小程序。
project|Psets 0–8 与 Final Project|独立做命令行文本工具，读文件、统计词频、输出 JSON，附测试与说明。'''))
course('abstraction','Composing Programs · 程序抽象','code','02','CS50P 后、算法/CS188 前的实现桥接。',T('''higher|1.6 · 高阶函数|接口、组合与函数作为值。
recursion|1.7 · 递归函数|递归与迭代；终止条件、树遍历与表达式求值。
data|2.2 / 2.9 · 数据抽象与递归对象|容器、链表、树；拆分输入、算法与输出接口。'''),priority='桥接')
course('tools','MIT Missing Semester','code','02','固定 2020 版；每讲末尾 Exercises。Unix 练习可在 WSL/Linux 做。',T('''shell|Shell 与数据整理|管道、重定向、查找、退出码、日志筛选与环境变量。
git|Git 与实验版本|提交、分支、合并、diff、恢复；数据模型与源代码分开管理。
debug|调试与 profiling|定位错误、测量热点；Vim 与杂项按需。
build|依赖、构建与自动化|每门课程单独环境；配置、日志与一条命令复现。'''))
course('discrete','MIT 6.042J · 离散数学','math','02','算法和 CS188 的证明准备；按主题选读。',T('''logic|集合、函数与逻辑|命题、量词、关系与集合表达。
proof|归纳法与循环不变量|正确性论证、递归终止与基本证明技巧。
graph|图与离散概率|图表示、路径与组合推理。'''),edition='Spring 2015 · 核心选读')
course('algo','MIT 6.006 · 数据结构与算法','code','02','先用 PS0 检查 Python 与离散数学准备；核心主题不等于完整速成学期。',T('''complexity|L1–4 · 复杂度、排序与哈希|时间/空间复杂度；数组、接口、排序与哈希。
heap|L8 · 堆与优先队列|实现与使用 heapq；比较操作复杂度。
search|L9–10 · BFS / DFS|图表示、deque、环与重复状态；独立实现遍历。
dp|最短路径与动态规划|Dijkstra、子问题、记忆化与递推；解释最优子结构。'''),edition='Spring 2020 · 核心选读')
course('science','科学计算工具箱','code','02','官方教程配小型数据实验；先划分数据，再拟合预处理。',T('''numpy|NumPy · 形状与向量化|shape、axis、broadcasting、索引、@ 与 *、随机数。
pandas|pandas · 数据处理|读取、缺失值、过滤、分组、连接与类型。
plot|Matplotlib · 实验图|学习曲线、散点图、误差条、标注与保存。
eval|scikit-learn · 评估与数据边界|Pipeline、交叉验证、指标、数据泄漏与随机性。'''))
course('torch','PyTorch · Learn the Basics','code','02','和 D2L 配合；能独立写训练循环并保存、恢复预测。',T('''tensor|Tensor / autograd / Module|shape、dtype、device、计算图与模块参数。
train|Dataset 与训练循环|数据加载、梯度清零、优化器、train/eval 与 no_grad。
state|checkpoint 与复现|小 batch 过拟合自测、保存与重载、随机种子。'''),priority='桥接')
course('gates','G1–G4 · 能力衔接实践','code','10','本体系设计的验收任务，非学校官方额外要求；已有等价成果可不重复。',T('''g1|G1 · 程序与算法|独立实现 BFS/UCS，覆盖无解、环、重复状态、不同边权，并解释复杂度与正确性。
g2|G2 · 数学到张量|NumPy 实现平滑小网络的前后向；float64 有限差分核对，说明广播与 batch 维。
g3|G3 · 独立训练工程|数据、模型、配置、训练、评估、测试；恢复模型/优化器/步数与随机状态。可与 NLP 项目合并。
g4|G4 · 系统与性能|资源估算 + profiler；区分 FLOPs、时间、内存、I/O 与通信，正确处理 warm-up 和异步。'''),priority='桥接')
course('ng','Andrew Ng · ML Specialization','ml','03','采用新版 Python 三门专项。可用 ISLP 替代入门主线；评分作业权限依平台政策。',T('''supervised|监督学习 · 回归与分类|线性/逻辑回归、损失、梯度下降、正则化；NumPy 实现。
advanced|高级算法 · 网络与树模型|神经网络、偏差/方差、诊断、决策树与集成。
unsupervised|无监督、推荐与 RL 入门|聚类、异常检测、推荐；建立任务、输入、目标与指标的全景。'''),edition='新版 Python 专项')
course('islp','ISLP · 统计学习与 Python','ml','03','可替代 Andrew Ng，或仅补实验；作者免费书稿、概念题和官方 labs。',T('''model|Ch.2–4 · 统计学习、回归与分类|建立基线、目标函数与分类指标。
validation|Ch.5–6 · 重采样与正则化|交叉验证、bootstrap、模型选择、测试集边界。
tree|Ch.8–9 · 树与 SVM|比较逻辑回归、随机森林和 MLP，解释误差来源。
unsupervised|Ch.12 · 无监督学习|聚类与降维；Ch.7/10 等按缺口选读。'''),edition='Python 版 2023')
course('cs229','Stanford CS229 · 理论选读','ml','03','2022 官方讲义；按模型补推导，不是 D2L 的整门硬先修。',T('''likelihood|回归的概率解释与 MLE/MAP|高斯噪声 → 最小二乘；Bernoulli → 逻辑回归；L2 与先验。
kernel|生成/判别模型与核方法|SVM、核、泛化与正则化。
latent|隐变量、EM 与 PCA|推导 GMM 的 E/M 步；PCA 最大方差与最小重建误差。'''),priority='选读',edition='Fall 2022 notes')
course('cs188','Berkeley CS188 · 人工智能','ai','03','搜索可先开始，推断与 RL 等概率基础完成。公开 autograder 不等于官方成绩。',T('''search|P0–P1 · 搜索与约束|Python 热身；DFS/BFS/UCS/A*、启发函数与 CSP。
multi|P2 · 对抗决策|minimax、alpha-beta、expectimax；手算博弈树。
mdp|P3 · 序贯决策|MDP、value iteration、Q-learning；区分规划与学习。
bayes|P4 · 不确定性推理|Bayes 网络、变量消元、HMM、采样与粒子滤波。
learn|P5 · 机器学习|概率分类、感知机与神经网络；用固定学期代码和测试。'''),edition='Spring 2025')
course('d2l','动手学深度学习 · D2L','dl','04','PyTorch 主教材。每节 Exercises + 代码改动；旧竞赛不作为完成前提。',T('''prelim|预备知识 · 张量与自动微分|数据、线代、微积分与 autograd；shape 追踪与梯度检查。
mlp|线性模型与 MLP|从零/框架实现对照；正则化、dropout、损失与反传。
compute|深度学习计算|模块、初始化、参数、设备与保存/恢复。
cnn|CNN 与现代架构|卷积、池化、残差、归一化；训练小 CNN。
rnn|RNN / LSTM / GRU 与 seq2seq|变长序列、梯度问题、encoder-decoder。
attention|注意力与 Transformer|mask、位置编码、多头；实现并检查小型 attention。
optim|优化算法|SGD、momentum、Adam 与学习率。
perf|计算性能|硬件、同步、批量、并行；吞吐与资源估算。
apps|CV / NLP 应用|检测、分割、词向量与预训练，转专项深化。'''),edition='中文第二版 · PyTorch')
course('cs231','Stanford CS231n · 视觉','cv','04','基础与 A1/A2 保留；视觉方向做 A3 和消融项目，语言方向不必全修。',T('''a1|A1 · 分类与反向传播|kNN、softmax、全连接网络与梯度检查。
a2|A2 · CNN、训练与序列|归一化、dropout、CNN、可视化、RNN captioning。
vision|视觉架构与任务|迁移学习、检测/分割；对应课程 slides 与 notes。
a3|A3 · Transformer 与生成/多模态|Transformer captioning、自监督、扩散、CLIP/DINO。'''),edition='Spring 2025')
course('cs224','Stanford CS224n · NLP','nlp','04','2025 讲义/作业同版，2023 公开视频作概念辅助。2025 录像限注册学生。',T('''a1|A1 · 词向量|词表示、相似性与表示学习；官方 notebook。
a2|A2 · 网络与张量求导|神经网络基础、依存分析、形状和梯度。
a3|A3 · 神经机器翻译|RNN、seq2seq、attention、subwords 与变长序列。
a4|A4 · Transformer 与自监督|self-attention、预训练、迁移与微调。
project|Final Project · 独立 NLP 工程|minimalist GPT-2 或自定义实验；可和 G3 合并。检查数据边界、困惑度与生成样例。'''),edition='Winter 2025；公开视频 2023')
course('hf','Hugging Face · LLM Course','nlp','04','D2L 后、CS224n 中后段的工具实践，与从零实现互补。',T('''token|Tokenizer、datasets 与模型|预处理、padding、mask、加载预训练模型。
finetune|微调、PEFT 与评估|区分预训练/微调/测试数据；结合 LoRA 原论文理解低秩更新。
paper|Attention 原论文|先画清张量形状和目标函数，再读实验、基线与消融。'''),priority='补充')
course('zhao','赵世钰 · 强化学习的数学原理','rl','05','中文课程主线；官方公开英文书稿与 slides，中文纸书版本不同。环境代码不等于全部算法答案。',T('''mdp|Ch.1 · MDP 基本概念|状态、动作、策略、奖励、回报与终止条件。
bellman|Ch.2–3 · Bellman 方程|固定策略评价、最优价值与最优性；转移矩阵和线性求解。
planning|Ch.4 · 价值迭代与策略迭代|已知模型下规划；小问题比较精确解。
mc|Ch.5 · Monte Carlo|用完整轨迹估计价值；样本量与误差。
stochastic|Ch.6 · 随机逼近|步长、噪声与收敛条件；不随意推广表格保证到神经网络。
td|Ch.7 · TD、Sarsa、Q-learning|bootstrap、on/off-policy、偏差/方差。
approx|Ch.8 · 价值函数逼近|先线性逼近，再连接 DQN。
pg|Ch.9 · 策略梯度|REINFORCE、log-prob、baseline 与方差。
ac|Ch.10 · Actor-Critic|策略与价值联合学习；比较两种损失。'''))
course('wang','王树森 · 深度强化学习','rl','05','赵课后学习深度价值方法、策略方法与连续控制；部分条目未发布完整材料，实践另补。',T('''review|Overview 与 TD 复习|value / policy / actor-critic 定位与 n-step target。
dqn|Value-based 进阶|replay、target network、Double DQN、dueling。
pg|Policy gradient 与 baseline|REINFORCE、A2C、advantage 与方差控制。
trust|TRPO 与策略约束|策略变化、采样分布和概率比率，再连接 PPO。
continuous|连续控制|随机/确定性策略、DPG 与连续动作梯度。
multi|多智能体与扩展 · 选修|非平稳性、集中训练/分散执行；缺失材料转 CS285。'''))
course('rlpractice','R1–R5 · RL 编程实验','rl','05','本体系自设项目。Gymnasium 与历史 Gym 依赖分开；先验 return/mask/buffer，再看曲线。',T('''r1|R1 · 表格型闭环|Grid World：规划、MC、TD、Sarsa、Q-learning 与精确解比较。
r2|R2 · DQN → Double DQN|CartPole；replay/target 的消融与 TD target。
r3|R3 · REINFORCE → Actor-Critic|baseline、回报、梯度和样本效率。
r4|R4 · PPO|概率比、旧策略、clipping、advantage；CleanRL 是参考实现，不是赵/王官方作业。
r5|R5 · 连续控制与 SAC|Pendulum 等；动作范围、分布、探索、熵项；控制方向重点。
eval|可靠实验与终止处理|多种子、环境步数、版本；区分 terminated/truncated 与 bootstrap 目标。'''))
course('cs285','Berkeley CS285 · RL 进阶','rl','05','王课后优先 HW2/3，研究方向再扩展；原版本环境独立配置。',T('''hw1|HW1 · 模仿学习|imitation learning 与数据分布变化。
hw23|HW2–3 · 策略梯度、Q / AC|用完整编程作业检验理论到实现。
hw45|HW4–5 · 模型、探索与离线 RL|model-based RL、exploration 与 offline RL。'''),priority='选修',edition='Fall 2023')
course('silver','David Silver · RL 解释补充','rl','05','可选第二种解释来源，无需重复全修。',T('''overview|价值、策略与规划复习|在概念不清时查相应讲义与视频。'''),priority='选修')
course('c','CS50x · C 与内存选读','systems','09','Python 后补 C；指针、内存、编译与数据结构，为 CS:APP/OS 编程准备。',T('''basic|Week 1 · C 语言|类型、控制流、编译与基础调试。
memory|Week 4 · Memory|指针、数组、字符串、分配/释放与内存错误。
speller|Pset 5 · Speller|用数据结构和 C 实现字典；保留正确性测试。'''),edition='2025 · Weeks 1–5 选读')
course('csapp','CMU 15-213 / CS:APP','systems','09','数值表示、内存和性能为核心。Self-Study Labs 与授课版分别匹配；部分实验要求 Linux/x86-64。',T('''repr|Ch.2–3 · 表示与机器程序|整数、浮点、数组、指针、调用栈；Data Lab。
cache|Ch.5–6 · 优化与内存层次|局部性、cache、数据移动；Cache Lab 与分块矩阵实验。
process|Ch.8–10 · 进程、虚拟内存与 I/O|异常控制流、地址空间、文件；Shell Lab。
concurrent|Ch.11–12 · 网络与并发|多 worker、进程通信、同步；Malloc/Proxy Lab 按方向深化。
processor|Ch.4 · 处理器设计 · 选修|完整体系结构方向继续，不是开始 ML 的统一门槛。'''),edition='Fall 2015 + CS:APP 3e Labs')
course('ostep','OSTEP · 操作系统核心','systems','09','CS:APP 已会的部分用题目验收，只补薄弱处。模拟题可 Python，系统题需 C/Unix。',T('''process|Processes / Process API|进程创建、等待、隔离与 cpu-api 作业。
memory|Memory / Paging / TLB|虚拟地址、分页、地址转换与 vm-paging 模拟。
threads|Threads / Locks / Conditions|共享状态、竞态、死锁；有界生产者—消费者队列。
io|I/O 与文件系统基础|文件、存储与多 worker 数据读取；解释并行何时反而变慢。'''))
course('network','Computer Networks · Systems Approach','systems','09','作者书稿与 slides；先补能解释通信的核心，不要求先实现完整协议栈。',T('''latency|Foundation · 延迟与带宽|分组、延迟、吞吐；估算发送张量的时间并注明假设。
transport|IP / TCP / UDP / RPC|进程间传输、可靠性、消息边界、超时与拥塞控制目的。
application|DNS / HTTP 与 socket 实验|本地两进程传消息并测量不同消息大小；不冒充多机 NCCL 性能。'''))
course('mlsys','ML 系统桥接 · Profiler / GPU','systems','09','D2L 后启动，A2 中继续深化；GPU 性能必须实测，不能用 CPU 推算替代。',T('''resource|资源估算与计算图|参数、梯度、优化器状态、激活与 dtype；训练/推理内存差异。
profiler|PyTorch Profiler|warm-up、异步计时；区分数据、CPU、传输、GPU 热点。
triton|Triton 基础算子热身|vector add、fused softmax、matmul；高性能 attention 留在 A2。
dist|PyTorch Distributed|rank/world size、数据划分、梯度同步与单/多卡结果。'''),priority='桥接')
course('xv6','MIT 6.1810 · OS 深化','systems','09','C、系统调用与基础体系结构之后再做；不是 CS336 A1 门槛。',T('''kernel|xv6 阅读与内核实验|完整 OS 方向：按课程 schedule 阅读和实验。'''),priority='选修',edition='Fall 2024')
course('cs144','Stanford CS144 · 网络深化','systems','09','需要现代 C++ 与 Linux；按所选学期检查发布完整性。',T('''tcp|网络协议栈实验|完整 TCP/网络训练，非 ML 统一前置。'''),priority='选修',edition='原文核验：Fall 2026')
course('dlsys','CMU 10-414/714 · DL Systems','systems','09','需要 Python/C++、ML 与数学；用于框架和 GPU 系统方向深化。',T('''framework|自动微分框架与算子后端|框架实现、C++/CUDA 后端、算子优化；不强制在 CS336 前全修。'''),priority='选修')
course('cs336','Stanford CS336 · 从零构建语言模型','lm','06','固定 Spring 2025 手册与 Git SHA。脚手架少，按 A1/A2/A5 分阶段准备；课程服务和 GPU 资源另依权限。',T('''a1|A1 · Tokenization 与基本模型|BPE、Transformer、优化器、训练、生成与 checkpoint。G2/G3 在此前验收。
a2|A2 · 系统效率|profiling、FlashAttention/Triton、分布式与内存；G4 在此前，深入 kernel 与并行在课内学。
a3|A3 · 规模规律|模型/数据/算力取舍与 scaling 拟合；无课程 API 可做标明范围的小规模替代实验。
a4|A4 · 数据工程|清洗、过滤、去重、流水线和质量比较；注意数据权限与版本。
a5|A5 · 对齐与推理 RL|SFT、策略优化、GRPO、推理奖励、评估；safety/DPO 补充为选做。'''),edition='Spring 2025 · 固定历史提交')
course('capstone','综合实践 · 小型语言模型','lm','06','本体系最终项目。模型规模随可用资源；保留数据、代码、指标、消融与局限。',T('''data|任务、数据与基线|许可、划分、去重、tokenizer、简单基线。
experiment|训练、消融与生成评估|token 数、损失、吞吐、内存；只改一个主要变量比较。
report|复现报告与局限|README、依赖、命令、结果；区分借用组件与自实现，区分缩小实验与原作业复现。'''))

# Sources: attach only URLs already present in the checked Markdown/version manifest.
RULES = [
 ('18-06','la'),('18-01','calc1'),('18-02','calc2'),('res-6-012','prob'),('6-041sc','prob'),('18-05','stats'),
 ('mml-book','mml'),('cvxbook','convex'),('harvard.edu/python','python'),('composingprograms','abstraction'),
 ('missing.csail','tools'),('6-042j','discrete'),('6-006','algo'),('numpy.org','science'),('pandas.pydata','science'),('matplotlib','science'),('scikit-learn','science'),
 ('beginner/basics','torch'),('machine-learning-introduction','ng'),('deeplearning.ai','ng'),('statlearning.com','islp'),('ISLP_labs','islp'),('cs229','cs229'),
 ('cs188','cs188'),('CS188','cs188'),('d2l','d2l'),('berkeley-stat-157','d2l'),('cs231n','cs231'),('2fq9wYslV0A','cs231'),('cs224n','cs224'),('PLoROMvodv4rMFqRtEuo6SGjY4XbRIVRd4','cs224'),
 ('huggingface','hf'),('1706.03762','hf'),('2106.09685','hf'),('MathFoundationRL','zhao'),('shiyuzhao','zhao'),('2044042934','zhao'),('wangshusen','wang'),
 ('gymnasium','rlpractice'),('1707.06347','rlpractice'),('cleanrl','rlpractice'),('1801.01290','rlpractice'),('deeprlcourse','cs285'),('davidstarsilver','silver'),
 ('harvard.edu/x','c'),('15213','csapp'),('csapp.cs','csapp'),('OSTEP','ostep'),('ostep-homework','ostep'),('SystemsApproach','network'),
 ('profiler_recipe','mlsys'),('triton-lang','mlsys'),('dist_overview','mlsys'),('6.1810','xv6'),('cs144','cs144'),('dlsyscourse','dlsys'),
 ('cs336','cs336'),('SQ3fZ1sAqXI','cs336'),('PLoROMvodv4rOY23Y0BoGoBGgQ1zmU_MT_','cs336')]

def resource_title(url, labels):
    label = max(labels, key=len)
    if 'assignments_w25/' in url:
        name = url.rsplit('/',1)[-1]; label = 'CS224n '+name.split('.')[0].upper()+(' · 题面 PDF' if name.endswith('pdf') else ' · 代码 ZIP')
    if 'cs336_spring2025_assignment' in url:
        num = re.search(r'assignment(\d)',url).group(1)
        label = 'CS336 A'+num+(' · Safety/RLHF 补充手册' if 'supplement' in url else ' · 2025 手册 PDF')
    if 'stanford-cs336/assignment' in url and '/tree/' in url: label = 'CS336 A'+re.search(r'assignment(\d)',url).group(1)+' · 固定代码'
    if 'stanford-cs336/assignment' in url and 'README.md' in url: label = 'CS336 A'+re.search(r'assignment(\d)',url).group(1)+' · 固定 README'
    return label

for url, info in URLS.items():
    owner = next((c for pattern,c in RULES if pattern in url), None)
    assert owner, ('Unmapped URL',url)
    key = 'r.'+hashlib.sha1(url.encode()).hexdigest()[:12]
    # Common course sources live under a genuine third-level navigation node.
    nav = owner+'.materials'
    if nav not in INDEX: node(nav,'课程材料与章节导航','topic',owner,description='从官方课程表、教材目录、视频或代码入口查找对应章节。具体主题的直达链接同时挂在各主题下。')
    title = resource_title(url,info['labels'])
    lower = (url+' '+title).lower()
    kind = '课程 / 教材'
    if any(s in lower for s in ['assignment','psets','problem','labs','作业','习题','resource-index']): kind = '作业 / 实验'
    if any(s in lower for s in ['slides','notes','讲义','课件']): kind = '讲义 / 课件'
    if any(s in lower for s in ['youtube','bilibili','视频']): kind = '视频'
    if '/abs/' in url: kind = '原论文'
    if 'github.com' in url and not url.endswith('.pdf'): kind = '源码 / 仓库' if '/tree/' not in url or 'assignment' in url else '资料目录'
    if url.endswith('.zip'): kind = '作业代码 ZIP'
    note = '沿用本地路线已核验入口；资源本体仍在原站，图谱不提供离线镜像。'
    if owner=='ng': note = '课程内容与评分作业权限依平台及账户；不承诺全部免费。'
    elif owner=='cs336' and 'assignment' in url: note = '锁定 Spring 2025 历史提交；勿跳到默认分支混用。课程服务及设备条件另查手册。'
    elif owner=='cs224' and 'youtube' not in url: note = 'Winter 2025 归档；当学期录像限注册学生，公开辅助视频为 2023。'
    node(key,title,'resource',nav,url=url,resourceKind=kind,description=note,sourceDocs=info['docs'],aliases=info['labels'])

def attach(topic, *patterns):
    matches = [n for n in NODES if n['type']=='resource' and any(p in n['url'] for p in patterns)]
    assert matches, (topic,patterns)
    for n in matches: edge(topic,n['id'],'contains','学习资料', '资料入口与主题对应；若为总目录，请在原站按本主题定位。')

def all_topics(c, *patterns):
    for n in list(NODES):
        if n.get('parent')==c and not n['id'].endswith('.materials'): attach(n['id'],*patterns)

for c,patterns in {
 'la':['18-06sc'], 'calc1':['18-01sc'], 'calc2':['18-02sc'], 'prob':['res-6-012','6-041sc'], 'stats':['18-05'], 'mml':['mml-book'], 'convex':['cvxbook'],
 'python':['harvard.edu/python/psets/'], 'tools':['missing.csail'], 'discrete':['6-042j'], 'algo':['6-006-introduction-to-algorithms-spring-2020/pages/assignments/','6-006-introduction-to-algorithms-spring-2020/pages/resource-index/'],
 'torch':['beginner/basics'], 'ng':['machine-learning-introduction'], 'islp':['statlearning.com','ISLP_labs'], 'cs229':['cs229'],
 'cs188':['cs188/archive/sp25/projects/','cs188/textbook'], 'd2l':['zh.d2l.ai','courses.d2l.ai','d2l-ai/d2l-zh'],
 'zhao':['Book-all-in-one.pdf','Lecture%20slides'], 'wang':['wangshusen/DRL/tree/master/Slides','Notes_CN'],
 'cs285':['homework_fall2023','deeprlcourse-fa23'], 'silver':['davidstarsilver'], 'ostep':['OSTEP','ostep-homework'],
 'network':['SystemsApproach'], 'xv6':['6.1810'], 'cs144':['cs144'], 'dlsys':['dlsyscourse'],
 'cs336':['cs336.stanford.edu/spring2025','spring2025-lectures']
}.items(): all_topics(c,*patterns)

SPECIFIC = {
 'python.basics':['harvard.edu/python/weeks/0/'],
 'abstraction.higher':['16-higher'], 'abstraction.recursion':['17-recursive'], 'abstraction.data':['22-data','29-recursive'],
 'science.numpy':['numpy.org'], 'science.pandas':['pandas.pydata'], 'science.plot':['matplotlib'], 'science.eval':['scikit-learn'],
 'mml.info':['zh.d2l.ai'], 'cs231.a1':['assignments2025/assignment1/'], 'cs231.a2':['assignments2025/assignment2/'], 'cs231.a3':['assignments2025/assignment3/'], 'cs231.vision':['cs231n.stanford.edu/2025/schedule'],
 'cs224.a1':['assignments_w25/a1'], 'cs224.a2':['assignments_w25/a2'], 'cs224.a3':['assignments_w25/a3'], 'cs224.a4':['assignments_w25/a4'], 'cs224.project':['cs224n.1254/'],
 'hf.token':['huggingface'], 'hf.finetune':['huggingface','2106.09685'], 'hf.paper':['1706.03762'],
 'rlpractice.r1':['Code%20for%20grid%20world'], 'rlpractice.r2':['gymnasium'], 'rlpractice.r3':['gymnasium'], 'rlpractice.r4':['1707.06347','cleanrl'], 'rlpractice.r5':['1801.01290','gymnasium'], 'rlpractice.eval':['gymnasium'],
 'c.basic':['x/2025/weeks/1'], 'c.memory':['x/2025/weeks/4'], 'c.speller':['x/2025/psets/5'],
 'csapp.repr':['csapp.cs','15213-f15/www/schedule'], 'csapp.cache':['csapp.cs','11-memory-hierarchy','12-cache-memories'], 'csapp.process':['csapp.cs','15213-f15/www/schedule'], 'csapp.concurrent':['csapp.cs','15213-f15/www/schedule'], 'csapp.processor':['15213-f15/www/schedule'],
 'mlsys.resource':['zh.d2l.ai','spring2025-lectures'], 'mlsys.profiler':['profiler_recipe'], 'mlsys.triton':['triton-lang'], 'mlsys.dist':['dist_overview'],
 'gates.g1':['6-006-introduction-to-algorithms-spring-2020/pages/assignments/'], 'gates.g2':['mml-book','numpy.org'], 'gates.g3':['beginner/basics','cs224n.1254/'], 'gates.g4':['profiler_recipe','12-cache-memories'],
 'capstone.data':['cs336.stanford.edu/spring2025/'], 'capstone.experiment':['spring2025-lectures'], 'capstone.report':['missing.csail']
}
for topic, patterns in SPECIFIC.items(): attach(topic,*patterns)
for i in range(1,6): attach(f'cs336.a{i}',f'stanford-cs336/assignment{i}-')

# Local design relationships: a directional preparation recommendation is NOT
# a claim that a university requires all preceding courses in full.
RELATIONS = '''
calc1|calc2|pre|基础衔接|一元导数、积分和链式法则支撑多元微积分。
la|mml|pre|数学桥接|矩阵运算与线性映射支撑向量/矩阵微积分。
calc2.grad|mml.matrix|pre|从标量到张量|偏导基础之后练 Jacobian 与矩阵链式法则。
calc1.integral|prob.continuous|pre|积分到概率|连续分布的归一化与期望使用积分。
prob|stats|pre|概率到统计|估计与检验建立在抽样分布和条件概率之上。
python|abstraction|pre|程序抽象|完成基础语法后训练递归、接口与组合。
abstraction|algo|pre|实现准备|递归与数据抽象是数据结构实现基础。
discrete|algo|pre|证明准备|集合、归纳、不变量与图支撑算法正确性。
python|tools|related|并行练习|工具链与 Python 项目交叉使用，无需等全部数学完成。
python|science|pre|计算工具|用函数、数组与测试组织数值实验。
science|torch|pre|张量准备|NumPy 的 shape/广播/向量化迁移到 Tensor。
algo|cs188|pre|算法准备|搜索部分调用图、队列、堆与复杂度知识。
prob|cs188|pre|分阶段补概率|Bayes/HMM/MDP 部分需要概率；不阻止搜索部分先学。
ng|islp|related|可替代与补充|二选一入门或按缺口补实验，不是重复全修的先后关系。
ng|cs229|related|推导深化|入门概念可在 CS229 对应模型中补数学。
islp|cs229|related|建模与推导|实验和数学推导互补，CS229 完整课不作 DL 硬先修。
ng|d2l|pre|ML 基础路径 A|掌握模型、损失与评估后进入 DL；可用 ISLP 等价替代。
islp|d2l|pre|ML 基础路径 B|统计学习核心可提供替代准备；无需与 Andrew Ng 全部重复。
torch|d2l|related|工具与教材配合|PyTorch 工具与 D2L 实现同步练习。
la.projection|cs229.likelihood|related|最小二乘的两种解释|几何投影与高斯似然导出同一平方误差目标。
la.svd|cs229.latent|related|SVD → PCA|中心化数据的低秩分解连接主成分与重建误差。
la.svd|hf.finetune|related|低秩结构|低秩矩阵思想连接 LoRA；LoRA 并不等于直接做 PCA。
la.eigen|mml.opt|related|曲率与优化|Hessian 特征值帮助解释步长与条件数。
stats.mle|cs229.likelihood|pre|似然建模|先会写似然，再连接正则化和 MAP。
stats.interval|islp.validation|related|估计不确定性|bootstrap 与重采样连接区间和模型比较。
stats.interval|rlpractice.eval|related|多种子评估|用均值和离散程度报告 RL 实验，避免只挑最好曲线。
science.eval|islp.validation|related|实验边界|Pipeline 与训练/验证/测试隔离支撑可靠模型选择。
discrete.proof|algo.search|related|正确性|循环不变量与图结构帮助证明搜索性质。
abstraction.recursion|cs188.multi|related|递归决策树|minimax 与 alpha-beta 以递归树遍历组织。
algo.heap|cs188.search|pre|优先队列|UCS/A* 用优先队列管理待扩展状态。
algo.search|gates.g1|pre|独立实现验收|从示范到独立 BFS/UCS，并测试环和无解情况。
gates.g1|cs188.search|pre|能力检查|能处理边界和解释复杂度后开始搜索项目。
prob.bayes|cs188.bayes|pre|条件独立与推断|Bayes 网络和 HMM 依赖条件概率与联合分布。
prob.markov|zhao.mdp|pre|状态转移|Markov 链为受动作影响的 MDP 提供概率背景。
cs188.mdp|zhao.planning|related|同一决策框架|CS188 P3 提供练习，赵课补 Bellman 数学；不是两门全修先后关系。
mml.matrix|d2l.mlp|pre|矩阵链式法则|反向传播需要形状正确的向量/矩阵求导。
mml.opt|d2l.optim|related|优化理论到实现|SGD 与 Adam 等训练算法放回目标函数理解。
mml.info|cs224.a4|related|语言模型损失|交叉熵与 KL 连接预测分布、预训练和评估。
science.numpy|gates.g2|pre|向量化实现|用 NumPy 写前后向，检查广播与求和维度。
mml.matrix|gates.g2|pre|梯度检查|解析梯度与 float64 有限差分互相验证。
gates.g2|cs231.a1|pre|反传准备|数值梯度检查支撑视觉基础作业。
gates.g2|cs224.a2|pre|张量准备|网络与张量求导需要独立形状推理。
d2l|cs231|pre|视觉专项基础|共同 DL 基础后进入 CV；不要求先全修 NLP。
d2l|cs224|pre|语言专项基础|共同 DL 与完整训练循环后进入 NLP；无需全修 CS231n。
d2l.mlp|wang.dqn|pre|函数逼近基础|DQN 用神经网络拟合价值，需要反传与训练经验。
d2l.cnn|cs231.a2|pre|CNN 深化|从卷积基础进入严格训练和可视化实验。
d2l.rnn|cs224.a3|pre|序列建模|变长序列和 encoder-decoder 连接翻译任务。
d2l.attention|cs224.a4|pre|注意力基础|mask、多头与位置编码支撑自监督 Transformer。
d2l.attention|cs231.a3|related|跨模态结构|attention 同时用于图像描述与语言模型。
cs231.a3|cs224.a4|related|Transformer 共享|视觉和语言共享机制，但任务/数据/评价不同，无整课先后要求。
d2l|hf|pre|框架基础|先会训练与评估，再用预训练模型工具链。
cs224.a3|hf.token|related|分词与序列边界|subwords、padding 与 mask 影响输入输出与评估。
cs224.a4|cs336.a1|pre|模型概念到独立实现|先理解自回归目标与 attention，再在 A1 实现内部机制。
tools.build|gates.g3|pre|工程组织|独立配置、依赖、命令与日志是训练工程的一部分。
python.tests|gates.g3|pre|测试习惯|边界用例、异常和状态检查进入完整训练器。
torch.state|gates.g3|pre|状态恢复|从基础保存加载提升到优化器/步数/随机状态恢复。
cs224.project|gates.g3|related|可合并项目|NLP Final Project 可同时提供 G3 工程证据，不重复训练大模型。
gates.g3|cs336.a1|pre|A1 工程准备|能独立组织训练闭环；不要求提前重做完整 BPE/Transformer。
gates.g2|cs336.a1|pre|A1 张量准备|独立梯度和 shape 检查支撑从零模型实现。
python|c|pre|系统编程起步|掌握一般程序设计后补 C 类型、指针与内存。
c|csapp|pre|C 与指针|系统课代码和实验需要 C 与基本内存操作。
tools.shell|csapp.process|pre|Linux 工具|Shell 与命令行准备帮助完成 Unix 系统实验。
csapp|ostep|related|按缺口补齐|OS 概念有重叠，用作业检查再补薄弱部分。
c.memory|ostep.memory|pre|内存接口|指针与分配行为连接虚拟地址、页与地址转换。
csapp.cache|mlsys.profiler|pre|数据移动与瓶颈|局部性与内存层次是解释 profiler 热点的基础。
csapp.cache|cs336.a2|pre|A2 内存准备|数据移动与分块思想连接 attention 优化；CPU cache 不等于 GPU shared memory。
ostep.threads|torch.train|related|DataLoader 并发|进程/线程、同步和共享状态解释 worker 性能及错误。
ostep.threads|mlsys.dist|pre|同步概念|从进程与共享状态理解训练同步。
network.latency|mlsys.dist|pre|通信成本|带宽/延迟帮助分析分布式传输；多机实验前补齐。
network.transport|cs336.a2|related|跨机通信|基础通信为 collective 铺垫，完整 TCP 实现不是前置。
d2l.perf|mlsys.resource|pre|资源分析|从批量与设备概念进入参数、激活和优化器状态估算。
mlsys.profiler|gates.g4|pre|正确测量|warm-up 与异步计时进入性能验收。
csapp.cache|gates.g4|pre|内存实验|缓存练习提供解释资源瓶颈的证据。
gates.g4|cs336.a2|pre|A2 性能准备|先会区分正确性、吞吐、显存和通信，再做优化。
mlsys.triton|cs336.a2|related|A2 热身与同期学习|基础算子教程可在 A2 前/同期做，深入 attention 在原课学习。
mlsys.dist|cs336.a2|related|并行概念|rank/同步先建立，分片、通信重叠和优化在课内深化。
ostep|xv6|pre|OS 深化|基本系统概念与 C 后再读 xv6；非 AI 统一必修。
network|cs144|pre|网络深化|另需现代 C++ 与 Linux，再做协议栈实验。
d2l|dlsys|pre|系统方向选修|另需 C++ 与数学，完整框架课不作 CS336 硬先修。
prob|zhao|pre|RL 概率基础|条件期望、抽样、Markov 转移等按章节准备。
la.space|zhao.bellman|related|Bellman 线性系统|固定策略评价可写成线性方程并与迭代解比较。
prob.limit|zhao.stochastic|related|随机估计|样本均值、噪声与收敛条件连接随机逼近。
zhao.stochastic|d2l.optim|related|SGD 与随机逼近|理解随机梯度噪声及步长条件，不能无条件套用收敛保证。
zhao|wang|pre|数学到深度 RL|保留函数逼近、策略梯度与 actor-critic；重叠内容可自测跳过。
zhao.planning|rlpractice.r1|pre|表格型验证|先用精确解验算法，再看采样误差。
wang.dqn|rlpractice.r2|pre|深度价值实践|用实验检验 replay、target、Double DQN 的行为。
zhao.pg|rlpractice.r3|pre|策略优化实践|正确算 return/log-prob/baseline，再训练环境。
wang.trust|rlpractice.r4|pre|PPO 准备|策略约束与概率比率连接 clipping。
wang.continuous|rlpractice.r5|pre|连续动作准备|动作分布、梯度与探索是 SAC 的基础。
rlpractice.r3|cs285.hw23|related|完整作业检验|用官方 HW2/3 补脚手架、测试和实验。
zhao.pg|cs336.a5|pre|A5 策略梯度|将 log-prob、采样与梯度估计带入语言模型后训练。
wang.pg|cs336.a5|pre|A5 baseline / advantage|方差控制和优势估计连接奖励优化。
rlpractice.r4|cs336.a5|related|概率比与约束|PPO 经验帮助理解后训练；GRPO 在 A5 学，SAC 非统一前置。
stats.interval|cs336.a3|pre|受控实验|估计不确定性与模型比较支撑缩放规律拟合。
science.eval|cs336.a3|pre|验证边界|保持数据/评估一致，避免用测试集调规模规律。
science.pandas|cs336.a4|pre|数据流准备|读写、过滤、类型和版本为高级流水线打底。
algo.complexity|cs336.a4|related|哈希与去重|复杂度和哈希思想支持大规模数据处理。
algo.complexity|cs336.a1|related|BPE 工程|数据结构和复杂度影响 tokenizer 实现效率。
cs336.a1|cs336.a2|pre|正确性先于优化|基于正确模型做 profiling 与 kernel/并行实验。
cs336.a1|cs336.a3|pre|模型与训练基础|在完整训练闭环上比较模型、数据与算力。
cs336.a1|cs336.a4|pre|数据影响模型|用可复现模型衡量清洗与过滤效果。
cs336.a1|cs336.a5|pre|语言模型训练基础|自回归模型和训练管线支撑 SFT 与 RL。
cs336.a3|cs336.a4|related|数据与计算预算|数据质量/规模会影响计算效率与损失比较。
cs336|capstone|pre|综合闭环|将数据、模型、性能与评估整理成可复现项目。
capstone.experiment|rlpractice.eval|related|共同实验标准|保留基线、随机性、评价条件与局限。
'''
for row in RELATIONS.strip().split('\n'):
    s,t,k,label,reason = row.split('|',4)
    assert s in INDEX and t in INDEX,(s,t)
    edge(s,t,k,label,reason)

# Cross-domain overview links are conceptual summaries, not extra prerequisites.
for s,t,label,why in [
 ('math','ml','数学 → 建模','线代、概率、统计和优化提供建模语言。'),
 ('code','dl','实现与实验','张量、测试与训练工程使 DL 理论可验证。'),
 ('systems','lm','性能与规模','系统并行线在 CS336 A2 汇入。'),
 ('rl','lm','奖励与后训练','策略优化基础在 CS336 A5 汇入。'),
 ('dl','cv','视觉应用','卷积、attention 和优化在视觉任务中深化。'),
 ('dl','nlp','语言应用','序列与 attention 支撑 NLP。'),
 ('nlp','lm','从任务到实现','语言建模概念连接 CS336 从零实现。'),
 ('ai','rl','决策框架','MDP 与规划连接强化学习。'),
]: edge(s,t,'related',label,why)

# Initial effort estimates are editable planning weights, NOT official course
# durations. They include reading, derivation and the suggested practice scope.
HOURS = {
 'la':[14,12,12,10], 'calc1':[12,10,18,10], 'calc2':[8,16,16,8],
 'prob':[10,10,14,12,14], 'stats':[10,10,10], 'mml':[12,8,12,6], 'convex':[16,12,12],
 'python':[12,12,12,24], 'abstraction':[6,10,12], 'tools':[8,6,6,6], 'discrete':[8,12,10],
 'algo':[16,8,12,20], 'science':[10,8,6,10], 'torch':[8,12,8], 'gates':[10,12,24,16],
 'ng':[24,24,20], 'islp':[24,18,20,12], 'cs229':[18,20,20], 'cs188':[24,16,20,24,16],
 'd2l':[10,20,12,24,24,24,14,12,20], 'cs231':[24,32,20,40], 'cs224':[10,24,32,32,48],
 'hf':[12,16,8], 'zhao':[4,10,10,8,10,14,12,14,14], 'wang':[6,16,14,14,16,12],
 'rlpractice':[20,24,24,32,32,10], 'cs285':[20,48,48], 'silver':[24],
 'c':[10,14,16], 'csapp':[24,28,28,24,20], 'ostep':[12,16,24,12],
 'network':[8,16,12], 'mlsys':[10,14,20,18], 'xv6':[100], 'cs144':[100], 'dlsys':[140],
 'cs336':[70,80,32,48,80], 'capstone':[24,60,20]
}
for c, estimates in HOURS.items():
    topics=[n for n in NODES if n.get('parent')==c and n['type']=='topic' and not n['id'].endswith('.materials')]
    assert len(topics)==len(estimates), (c,len(topics),len(estimates))
    for n, hours in zip(topics,estimates): n.update(trackable=True,estimatedHours=hours)
for n in NODES:
    n.setdefault('trackable', False)
    n['referenceOnly']=n['type']=='resource' or n['id'].endswith('.materials')

# Every subject has at least one source; local practice instructions are also
# embedded in the HTML through descriptions, even without sibling Markdown.
for n in NODES:
    if n['type']=='topic':
        assert any(e['source']==n['id'] and INDEX[e['target']]['type']=='resource' for e in EDGES), ('Topic without sources',n['id'])
for e in EDGES:
    assert e['source'] in INDEX and e['target'] in INDEX
    if e['type']=='contains':
        rank={'domain':0,'course':1,'topic':2,'resource':3}
        assert rank[INDEX[e['target']]['type']]==rank[INDEX[e['source']]['type']]+1,e
counts={k:sum(n['type']==k for n in NODES) for k in ['domain','course','topic','resource']}
META = dict(title='AI 学习图谱',updated='2026-11-11',counts=counts,relations=sum(e['type']!='contains' for e in EDGES),sourceCount=len(URLS),sourceFiles=list(DOCS),
    provenance='课程与链接来自本地学习路线；先修建议与知识关联为学习设计，不代表学校额外官方先修要求。共同入口按章节标题在原站定位。',
    sourceHashes={k:hashlib.sha256(v.encode()).hexdigest() for k,v in DOCS.items()})
META['progressPolicy']={'unit':'topic','weight':'estimatedHours','completion':'all learning children complete','estimateNote':'初始学时为阅读、推导与练习的粗估权重，可逐章修改；不是学校官方学时。资料链接和导航不重复计分。'}
DATA=dict(meta=META,nodes=NODES,edges=EDGES)
OUT=Path(__file__).resolve().parent
(OUT/'curriculum.json').write_text(json.dumps(DATA,ensure_ascii=False,indent=2),encoding='utf-8')
template=(OUT/'template.html').read_text(encoding='utf-8')
payload=json.dumps(DATA,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
app=(OUT/'app.js').read_text(encoding='utf-8').replace('/*__LAYOUT__*/',(OUT/'layout.js').read_text(encoding='utf-8'))
html=template.replace('/*__STYLE__*/',(OUT/'style.css').read_text(encoding='utf-8')).replace('/*__DATA__*/',payload).replace('/*__PROGRESS__*/',(OUT/'progress.js').read_text(encoding='utf-8')).replace('/*__APP__*/',app)
(ROOT/'AI学习图谱.html').write_text(html,encoding='utf-8')
print(json.dumps(dict(nodes=len(NODES),edges=len(EDGES),**META),ensure_ascii=False,indent=2))
