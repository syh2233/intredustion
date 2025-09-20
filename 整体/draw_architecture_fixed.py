import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle
import numpy as np
import matplotlib.patheffects as path_effects

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 创建画布
fig, ax = plt.subplots(1, 1, figsize=(16, 12))
ax.set_xlim(0, 16)
ax.set_ylim(0, 12)
ax.axis('off')

# 定义颜色主题
colors = {
    'sensor': '#FF6B6B',      # 红色系 - 传感器
    'processing': '#4ECDC4',   # 青色系 - 数据处理
    'display': '#45B7D1',     # 蓝色系 - 显示报警
    'network': '#96CEB4',     # 绿色系 - 网络通信
    'web': '#FFEAA7',         # 黄色系 - Web监控
    'module_bg': '#F8F9FA',   # 模块背景色
    'border': '#2D3436',      # 边框色
    'text': '#2D3436',        # 文字色
    'arrow': '#74B9FF'        # 箭头色
}

# 创建阴影效果
def add_shadow(patch, dx=0.05, dy=0.05, alpha=0.3):
    shadow = patches.FancyBboxPatch(
        (patch.get_x() + dx, patch.get_y() + dy),
        patch.get_width(), patch.get_height(),
        boxstyle=patch.get_boxstyle(),
        facecolor='gray', alpha=alpha, zorder=patch.get_zorder()-1
    )
    ax.add_patch(shadow)

# 绘制主标题
title = ax.text(8, 11.5, '基于ESP32的宿舍火灾报警系统架构', 
                fontsize=24, fontweight='bold', ha='center', va='center',
                color=colors['text'])
title.set_path_effects([path_effects.withStroke(linewidth=3, foreground='white')])

# 绘制ESP32核心控制
esp32_box = FancyBboxPatch((6.5, 5), 3, 2, 
                           boxstyle="round,pad=0.1", 
                           facecolor='#E17055', 
                           edgecolor=colors['border'], 
                           linewidth=2,
                           zorder=10)
add_shadow(esp32_box)
ax.add_patch(esp32_box)
ax.text(8, 6, 'ESP32\n主控制器', fontsize=14, fontweight='bold', 
        ha='center', va='center', color='white')

# 定义模块位置和大小
modules = [
    {
        'name': '传感器数据采集模块',
        'color': colors['sensor'],
        'pos': (1, 8.5),
        'size': (3.5, 2),
        'submodules': [
            ('火焰传感器', 'flame'),
            ('MQ-2烟雾传感器', 'smoke'),
            ('数据滤波预处理', 'filter')
        ]
    },
    {
        'name': '数据处理与判断模块',
        'color': colors['processing'],
        'pos': (5.5, 8.5),
        'size': (3.5, 2),
        'submodules': [
            ('阈值判断算法', 'threshold'),
            ('防误报逻辑', 'anti_false'),
            ('报警状态管理', 'status')
        ]
    },
    {
        'name': '本地显示与报警模块',
        'color': colors['display'],
        'pos': (10, 8.5),
        'size': (3.5, 2),
        'submodules': [
            ('OLED显示控制', 'oled'),
            ('风扇报警控制', 'fan'),
            ('本地状态指示', 'led')
        ]
    },
    {
        'name': '网络通信模块',
        'color': colors['network'],
        'pos': (1, 2.5),
        'size': (6, 2),
        'submodules': [
            ('Wi-Fi连接管理', 'wifi'),
            ('HTTP数据传输', 'http'),
            ('MQTT实时通信', 'mqtt'),
            ('断网重连机制', 'reconnect')
        ]
    },
    {
        'name': 'Web监控模块',
        'color': colors['web'],
        'pos': (8, 2.5),
        'size': (5.5, 2),
        'submodules': [
            ('实时数据展示', 'realtime'),
            ('历史数据查询', 'history'),
            ('设备状态监控', 'device'),
            ('报警记录管理', 'alert')
        ]
    }
]

# 绘制各个模块
for i, module in enumerate(modules):
    x, y = module['pos']
    w, h = module['size']
    
    # 绘制模块背景
    module_box = FancyBboxPatch((x, y), w, h,
                               boxstyle="round,pad=0.1",
                               facecolor=module['color'],
                               edgecolor=colors['border'],
                               linewidth=2,
                               alpha=0.8,
                               zorder=5)
    add_shadow(module_box)
    ax.add_patch(module_box)
    
    # 绘制模块标题
    ax.text(x + w/2, y + h - 0.3, module['name'], 
            fontsize=12, fontweight='bold', 
            ha='center', va='center', color='white')
    
    # 绘制子模块
    sub_h = (h - 0.6) / len(module['submodules'])
    for j, (sub_name, sub_key) in enumerate(module['submodules']):
        sub_y = y + 0.3 + j * sub_h
        
        # 子模块背景
        sub_box = FancyBboxPatch((x + 0.2, sub_y - 0.15), w - 0.4, sub_h - 0.1,
                                boxstyle="round,pad=0.05",
                                facecolor='white',
                                edgecolor=module['color'],
                                linewidth=1,
                                alpha=0.9,
                                zorder=6)
        ax.add_patch(sub_box)
        
        # 子模块文字
        ax.text(x + w/2, sub_y, sub_name, 
                fontsize=9, 
                ha='center', va='center', 
                color=colors['text'])

# 绘制传感器图标
sensor_icons = [
    {'pos': (0.5, 9.5), 'color': '#FF7675', 'label': '火焰'},
    {'pos': (1.2, 9.5), 'color': '#74B9FF', 'label': '烟雾'},
    {'pos': (1.9, 9.5), 'color': '#00B894', 'label': '温度'}
]

for icon in sensor_icons:
    circle = Circle(icon['pos'], 0.15, facecolor=icon['color'], 
                   edgecolor=colors['border'], linewidth=1, zorder=8)
    ax.add_patch(circle)
    ax.text(icon['pos'][0], icon['pos'][1], icon['label'][0], 
            fontsize=8, fontweight='bold', ha='center', va='center', 
            color='white')

# 使用简单的箭头绘制连接线
def draw_arrow(start, end, style='straight'):
    if style == 'straight':
        ax.annotate('', xy=end, xytext=start,
                   arrowprops=dict(arrowstyle='->', color=colors['arrow'], 
                                 lw=2, alpha=0.8))
    elif style == 'curved':
        # 计算控制点创建曲线
        mid_x = (start[0] + end[0]) / 2
        mid_y = (start[1] + end[1]) / 2 + 0.5
        ax.annotate('', xy=end, xytext=start,
                   arrowprops=dict(arrowstyle='->', color=colors['arrow'], 
                                 lw=2, alpha=0.8, 
                                 connectionstyle=f"arc3,rad=0.3"))

# 绘制连接线 - 完整的数据流向
connections = [
    # 传感器模块 -> ESP32
    ((2.75, 8.5), (6.5, 7), 'curved'),
    
    # 数据处理模块 <-> ESP32 (双向)
    ((7.25, 8.5), (8, 7), 'straight'),
    ((8, 7), (7.25, 8.5), 'straight'),
    
    # ESP32 -> 显示报警模块
    ((9.5, 6), (11.75, 8.5), 'curved'),
    
    # ESP32 -> 网络通信模块
    ((7, 5), (4, 4.5), 'curved'),
    
    # 网络通信模块 -> Web监控模块
    ((7, 3.5), (10.75, 3.5), 'straight'),
    
    # 数据处理模块 -> 传感器模块 (反馈)
    ((5.5, 9.5), (4.5, 9.5), 'straight'),
    
    # Web监控模块 -> 网络通信模块 (控制指令)
    ((10.75, 3), (7, 3), 'straight')
]

for start, end, style in connections:
    draw_arrow(start, end, style)

# 绘制数据流向标注
data_flow_labels = [
    (4.5, 7.8, '传感器数据'),
    (8.5, 7.8, '处理结果'),
    (8.5, 6.2, '控制指令'),
    (5.5, 4, '网络数据'),
    (10.5, 7.8, '报警信息'),
    (9, 3.8, 'Web数据'),
    (5, 10, '反馈信号'),
    (9, 2.5, '控制指令')
]

for x, y, label in data_flow_labels:
    ax.text(x, y, label, fontsize=9, ha='center', va='center',
            bbox=dict(boxstyle="round,pad=0.2", facecolor='white', 
                     edgecolor=colors['arrow'], alpha=0.8),
            color=colors['text'])

# 添加版本信息
version_text = ax.text(15.5, 0.5, 'v1.0', fontsize=10, 
                     ha='right', va='bottom', 
                     color=colors['text'], alpha=0.6)

# 添加边框装饰
border_rect = Rectangle((0.2, 0.2), 15.6, 11.6, 
                       linewidth=3, 
                       edgecolor=colors['border'], 
                       facecolor='none',
                       alpha=0.5)
ax.add_patch(border_rect)

# 添加背景渐变效果
gradient = np.linspace(0, 1, 100).reshape(1, -1)
gradient = np.vstack((gradient, gradient))
ax.imshow(gradient, extent=[0, 16, 0, 12], aspect='auto', alpha=0.1, cmap='Blues')

# 调整布局
plt.tight_layout()
plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)

# 保存图片
output_path = 'C:/手动D/行业实践/esp32_fire_alarm_architecture.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight', 
            facecolor='white', edgecolor='none')

print(f"架构图已保存到: {output_path}")

# 显示图片
plt.show()