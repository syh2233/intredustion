import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, ConnectionPatch, Circle, Rectangle
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

# 绘制连接线和箭头
connections = [
    # 传感器到ESP32
    ((2.75, 8.5), (6.5, 6.5)),
    # 数据处理到ESP32
    ((7.25, 8.5), (8, 7)),
    # 显示报警到ESP32
    ((10, 8.5), (9.5, 7)),
    # ESP32到网络通信
    ((8, 5), (4, 4.5)),
    # 网络通信到Web监控
    ((7, 3.5), (8, 3.5)),
    # ESP32到显示报警
    ((9.5, 6), (11.75, 8.5))
]

for start, end in connections:
    arrow = ConnectionPatch(xyA=end, xyB=start, coordsA='data', coordsB='data',
                           axesA=ax, axesB=ax,
                           connectionstyle="arc3,rad=0.3",
                           arrowstyle='->', 
                           mutation_scale=20, 
                           linewidth=2, 
                           color=colors['arrow'],
                           alpha=0.8,
                           zorder=3)
    ax.add_patch(arrow)

# 绘制数据流向标注
data_flow_labels = [
    (4.5, 7.8, '传感器数据'),
    (8.5, 7.8, '处理结果'),
    (6, 5.8, '控制指令'),
    (5.5, 4, '网络数据'),
    (10.5, 7.8, '报警信息')
]

for x, y, label in data_flow_labels:
    ax.text(x, y, label, fontsize=9, ha='center', va='center',
            bbox=dict(boxstyle="round,pad=0.2", facecolor='white', 
                     edgecolor=colors['arrow'], alpha=0.8),
            color=colors['text'])

# 绘制装饰性元素
# 添加一些装饰性的圆点
for i in range(20):
    x = np.random.uniform(0, 16)
    y = np.random.uniform(0, 12)
    circle = Circle((x, y), 0.02, facecolor=colors['arrow'], alpha=0.3)
    ax.add_patch(circle)

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

# 调整布局
plt.tight_layout()
plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)

# 保存图片
plt.savefig('/mnt/c/手动D/行业实践/esp32_fire_alarm_architecture.png', 
            dpi=300, bbox_inches='tight', 
            facecolor='white', edgecolor='none')

# 显示图片
plt.show()