"""变速（time-stretch）的一组基础契约函数。

每个函数对应一个具体的失效模式，且都可独立测试：

===============  ==================================================
window_size      自适应窗长：窗长随变速比伸缩，避免低频周期被破坏
pitch_preserve   保持音调：变速不改变基频
transient_gain   瞬态保护：对瞬态段额外增益，避免鼓点被相位抹平
phase_continuity 块边界相位：把相位差卷绕到主值区间，保证拼接连续
latency          延迟预算：把实时处理延迟计入总预算，保证音画同步
duration         时长：由样本数与采样率求真实时长
resample_ratio   重采样比：采样率切换时的转换比例
formant_shift    共振峰保持：抵消音调移动带来的共振峰漂移
crossfade        交叉淡化：块间重叠区的淡化权重
energy_normalize 能量归一：求达到目标能量所需的线性增益
block_boundary   块边界：样本在块内的偏移
speed_from_tempo 速度换算：节拍速度到播放倍率
align_tracks     多轨对齐：按变速比换算各轨时长
window_hop       窗跳：由窗长与重叠率求帧移
smooth_gain      增益平滑：逐帧向目标增益逼近，避免能量突变
===============  ==================================================

模块不依赖第三方库，仅使用标准库 ``math``。
"""

import math


def _check_positive(name, value):
    """校验参数为正数，否则抛出 ValueError。"""
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value!r}")


def window_size(rate, base):
    """自适应窗长。

    ``rate`` 为播放倍率（>1 表示加快）。加快时单帧覆盖的原信号变短，
    窗长按 ``base / rate`` 收缩；放慢时相反，从而在低频段仍保留足够
    的周期数以稳定相位估计。

    返回值取最接近的偶数（帧长对齐到 2 的倍数，便于 FFT 与重叠相加），
    且不小于 2。
    """
    _check_positive("rate", rate)
    _check_positive("base", base)
    size = base / rate
    return max(2, int(round(size / 2.0)) * 2)


def pitch_preserve(rate, pitch):
    """保持音调。

    变速只改变时长，不改变基频：无论 ``rate`` 为何，返回原音高
    ``pitch``（单位由调用方约定，如 Hz）。
    """
    _check_positive("rate", rate)
    return pitch


def transient_gain(transient, base):
    """瞬态保护。

    对瞬态段按强度 ``transient``（>=0，1 表示完整瞬态）在基础增益
    ``base`` 上做线性提升，返回 ``base * (1 + transient)``。瞬态处
    使用更短窗、更高增益，避免被相邻帧的相位平均抹平。
    """
    _check_positive("base", base)
    return base * (1.0 + max(0.0, transient))


def phase_continuity(previous, current):
    """块边界相位。

    返回相邻两块之间的相位差，并卷绕到 ``(-pi, pi]``，使拼接时
    相位连续、不产生周期性咔哒。差值本身就在主值区间时原样返回，
    保证整数/精确输入的输出不受浮点误差影响。
    """
    delta = current - previous
    if -math.pi <= delta <= math.pi:
        return delta
    wrapped = math.fmod(delta + math.pi, 2.0 * math.pi)
    if wrapped < 0:
        wrapped += 2.0 * math.pi
    return wrapped - math.pi


def latency(block, rate):
    """延迟预算。

    实时处理中一个处理块的延迟为 ``block * rate``（块时长乘以变速
    倍率），必须计入总延迟预算，否则口型与声音对不上。
    """
    _check_positive("block", block)
    _check_positive("rate", rate)
    return block * rate


def duration(samples, rate):
    """时长。

    采样率为 ``rate``（Hz）时，``samples`` 个样本对应的秒数。
    """
    _check_positive("rate", rate)
    return samples / rate


def resample_ratio(source, target):
    """重采样比。

    从采样率 ``source`` 转换到 ``target`` 时每个输入样本对应的输出
    样本数，切换采样率后据此重建滤波器/窗函数，避免高频镜像。
    """
    _check_positive("source", source)
    _check_positive("target", target)
    return target / source


def formant_shift(shift, rate):
    """共振峰。

    目标共振峰缩放系数为 ``shift``，而播放倍率 ``rate`` 会把共振峰
    一起移动 ``rate`` 倍；返回补偿系数 ``shift / rate``，使音色
    （而非音高）回到目标位置。
    """
    _check_positive("rate", rate)
    return shift / rate


def crossfade(index, total):
    """交叉淡化。

    重叠区内第 ``index`` 个样本（共 ``total`` 个）的淡化权重，取线性
    比例 ``index / total`` 并截断到 ``[0, 1]``。
    """
    if total <= 0:
        return 0.0
    return min(1.0, max(0.0, index / total))


def energy_normalize(energy, target):
    """能量归一。

    把当前能量 ``energy`` 拉到目标能量 ``target`` 所需的线性增益
    ``target / energy``。能量为零时无法归一，返回单位增益 1.0，
    避免静音段被无限放大。
    """
    if energy <= 0:
        return 1.0
    return target / energy


def block_boundary(index, block):
    """块边界。

    ``index`` 在其所属块内的偏移，即 ``index % block``。
    """
    _check_positive("block", block)
    return index % block


def speed_from_tempo(tempo, base):
    """速度换算。

    以 ``base`` 为基准节拍，当前 ``tempo`` 对应的播放倍率。
    """
    _check_positive("base", base)
    return tempo / base


def align_tracks(length, rate):
    """多轨对齐。

    变速后轨道长度按 ``length * rate`` 换算（``rate`` 为输出/输入
    比例），各轨统一用换算后的时长对齐，而不是只比较帧号。
    """
    _check_positive("rate", rate)
    return length * rate


def window_hop(window, overlap):
    """窗跳。

    窗长 ``window``、重叠率 ``overlap``（0..1）时的帧移，
    ``window * (1 - overlap)``，取整且至少为 1。
    """
    _check_positive("window", window)
    if not 0.0 <= overlap < 1.0:
        raise ValueError(f"overlap must be in [0, 1), got {overlap!r}")
    return max(1, int(round(window * (1.0 - overlap))))


def smooth_gain(current, target, step):
    """增益平滑。

    每帧把增益从 ``current`` 向 ``target`` 最多移动 ``step``，
    不过冲。用于分段变速的拼接处，避免能量突变造成可闻的跳变。
    """
    step = abs(step)
    if current < target:
        return min(target, current + step)
    return max(target, current - step)
