import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle
import numpy as np
import matplotlib.patheffects as path_effects

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 创建画布
fig, ax = plt.subplots(1, 1, figsize=(18, 14))
ax.set_xlim(0, 18)
ax.set_ylim(0, 14)
ax.axis('off')

# 定义颜色主题
colors = {
    'sensor': '#FF6B6B',      # 红色系 - 传感器
    'processing': '#4ECDC4',   # 青色系 - 数据处理
    'display': '#45B7D1',     # 蓝色系 - 显示报警
    'network': '#96CEB4',     # 绿色系 - 网络通信
    'web': '#FFEAA7',         # 黄色系 - Web监控
    'esp32': '#E17055',       # 橙色系 - ESP32核心
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

# 绘制标题框
title_box = FancyBboxPatch((5, 12.8), 8, 1.2, 
                           boxstyle="round,pad=0.1", 
                           facecolor='#6C5CE7', 
                           edgecolor=colors['border'], 
                           linewidth=3,
                           zorder=10)
add_shadow(title_box)
ax.add_patch(title_box)

# 绘制主标题
title = ax.text(9, 13.4, '基于ESP32的宿舍火灾报警系统架构', 
                fontsize=20, fontweight='bold', ha='center', va='center',
                color='white')
title.set_path_effects([path_effects.withStroke(linewidth=2, foreground='black')])

# 绘制ESP32核心控制
esp32_box = FancyBboxPatch((7.5, 6), 3, 2.5, 
                           boxstyle="round,pad=0.1", 
                           facecolor=colors['esp32'], 
                           edgecolor=colors['border'], 
                           linewidth=3,
                           zorder=10)
add_shadow(esp32_box)
ax.add_patch(esp32_box)
ax.text(9, 7.25, 'ESP32\n主控制器', fontsize=18, fontweight='bold', 
        ha='center', va='center', color='white')

# 定义模块位置和大小
modules = [
    {
        'name': '传感器数据采集模块',
        'color': colors['sensor'],
        'pos': (1, 9.5),
        'size': (4, 3.2),
        'submodules': [
            ('火焰传感器数据采集', 'flame'),
            ('MQ-2烟雾传感器数据采集', 'smoke'),
            ('数据滤波与预处理', 'filter')
        ]
    },
    {
        'name': '数据处理与判断模块',
        'color': colors['processing'],
        'pos': (6, 9.5),
        'size': (4, 3.2),
        'submodules': [
            ('阈值判断算法', 'threshold'),
            ('防误报逻辑', 'anti_false'),
            ('报警状态管理', 'status')
        ]
    },
    {
        'name': '本地显示与报警模块',
        'color': colors['display'],
        'pos': (11.5, 9.5),
        'size': (4, 3.2),
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
        'size': (7, 3.2),
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
        'pos': (9.5, 2.5),
        'size': (6, 3.2),
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
    ax.text(x + w/2, y + h - 0.5, module['name'], 
            fontsize=16, fontweight='bold', 
            ha='center', va='center', color='white')
    
    # 绘制子模块
    sub_h = (h - 1.0) / len(module['submodules'])
    for j, (sub_name, sub_key) in enumerate(module['submodules']):
        sub_y = y + 0.5 + j * sub_h
        
        # 子模块背景 - 更大的内边距和更粗的边框
        sub_box = FancyBboxPatch((x + 0.4, sub_y - 0.2), w - 0.8, sub_h - 0.3,
                                boxstyle="round,pad=0.1",
                                facecolor='white',
                                edgecolor=module['color'],
                                linewidth=2,
                                alpha=0.95,
                                zorder=6)
        ax.add_patch(sub_box)
        
        # 子模块文字 - 更大的字体和更好的对比度
        ax.text(x + w/2, sub_y, sub_name, 
                fontsize=15, 
                ha='center', va='center', 
                color='#2D3436',
                fontweight='bold',
                zorder=7)

# 绘制传感器图标 - 调整位置避免遮挡模块
sensor_icons = [
    {'pos': (1.2, 13.2), 'color': '#FF7675', 'label': '火'},
    {'pos': (2.2, 13.2), 'color': '#74B9FF', 'label': '烟'},
    {'pos': (3.2, 13.2), 'color': '#00B894', 'label': '温'},
    {'pos': (4.2, 13.2), 'color': '#FDCB6E', 'label': '气'},
    {'pos': (5.2, 13.2), 'color': '#A29BFE', 'label': '红'}
]

for icon in sensor_icons:
    circle = Circle(icon['pos'], 0.25, facecolor=icon['color'], 
                   edgecolor=colors['border'], linewidth=2, zorder=8)
    ax.add_patch(circle)
    ax.text(icon['pos'][0], icon['pos'][1], icon['label'][0], 
            fontsize=12, fontweight='bold', ha='center', va='center', 
            color='white')

# 使用简单的箭头绘制连接线
def draw_arrow(start, end, style='straight', color=colors['arrow'], alpha=0.8):
    if style == 'straight':
        ax.annotate('', xy=end, xytext=start,
                   arrowprops=dict(arrowstyle='->', color=color, 
                                 lw=2.5, alpha=alpha))
    elif style == 'curved':
        ax.annotate('', xy=end, xytext=start,
                   arrowprops=dict(arrowstyle='->', color=color, 
                                 lw=2.5, alpha=alpha, 
                                 connectionstyle=f"arc3,rad=0.3"))
    elif style == 'curved_rev':
        ax.annotate('', xy=end, xytext=start,
                   arrowprops=dict(arrowstyle='->', color=color, 
                                 lw=2.5, alpha=alpha, 
                                 connectionstyle=f"arc3,rad=-0.3"))

# 绘制完整的连接线系统
connections = [
    # 传感器图标 -> 传感器数据采集模块
    ((3.2, 13.0), (3, 12.7), 'straight', colors['sensor'], 0.8),
    ((3, 12.4), (3, 9.5), 'straight', colors['sensor'], 0.8),
    
    # 传感器模块 -> ESP32
    ((3, 9.5), (7.5, 7.5), 'curved'),
    
    # ESP32 -> 数据处理模块
    ((9, 8.5), (8, 9.5), 'curved_rev'),
    
    # 数据处理模块 -> ESP32 (反馈)
    ((8, 9.5), (9, 8.5), 'curved'),
    
    # ESP32 -> 显示报警模块
    ((10.5, 7.5), (13.5, 9.5), 'curved'),
    
    # ESP32 -> 网络通信模块
    ((7.5, 6), (4.5, 5), 'curved_rev'),
    
    # 网络通信模块 -> Web监控模块
    ((8, 3.75), (9.5, 3.75), 'straight'),
    
    # Web监控模块 -> 网络通信模块 (控制指令)
    ((9.5, 3.25), (8, 3.25), 'straight'),
    
    # 数据处理模块 -> 传感器模块 (配置反馈)
    ((6, 10.8), (5, 10.8), 'straight'),
    
    # ESP32内部处理循环
    ((7.5, 7.25), (6.5, 7.25), 'straight', colors['esp32'], 0.6),
    ((10.5, 7.25), (11.5, 7.25), 'straight', colors['esp32'], 0.6)
]

for start, end, style, *args in connections:
    color = args[0] if args else colors['arrow']
    alpha = args[1] if len(args) > 1 else 0.8
    draw_arrow(start, end, style, color, alpha)

# 绘制数据流向标注
data_flow_labels = [
    (3, 11, '传感器输入', colors['sensor']),
    (5, 8.5, '传感器数据', colors['sensor']),
    (8.5, 9, '算法处理', colors['processing']),
    (12, 8.5, '报警控制', colors['display']),
    (6, 5.5, '网络传输', colors['network']),
    (8.75, 4.2, 'Web数据', colors['web']),
    (5.5, 11.2, '配置反馈', colors['processing']),
    (9, 6.8, '内部处理', colors['esp32'])
]

for x, y, label, color in data_flow_labels:
    ax.text(x, y, label, fontsize=13, ha='center', va='center',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='white', 
                     edgecolor=color, alpha=0.9),
            color=colors['text'], fontweight='bold')

# 添加系统边框
system_border = Rectangle((0.5, 1.5), 16.5, 11.5, 
                         linewidth=3, 
                         edgecolor=colors['border'], 
                         facecolor='none',
                         alpha=0.7,
                         linestyle='--')
ax.add_patch(system_border)

# 添加图例
legend_items = [
    ('传感器数据采集', colors['sensor']),
    ('数据处理判断', colors['processing']),
    ('本地显示报警', colors['display']),
    ('网络通信', colors['network']),
    ('Web监控', colors['web']),
    ('ESP32主控', colors['esp32'])
]

legend_y = 0.8
for i, (label, color) in enumerate(legend_items):
    x_pos = 2 + i * 2.5
    # 图例色块
    legend_box = Rectangle((x_pos - 0.3, legend_y - 0.15), 0.6, 0.3,
                          facecolor=color, edgecolor=colors['border'],
                          alpha=0.8)
    ax.add_patch(legend_box)
    # 图例文字
    ax.text(x_pos, legend_y, label, fontsize=12, ha='center', va='center',
            color=colors['text'], fontweight='bold')

# 添加版本信息
version_text = ax.text(17.5, 0.3, 'v1.0', fontsize=10, 
                     ha='right', va='bottom', 
                     color=colors['text'], alpha=0.6)

# 添加背景渐变效果
gradient = np.linspace(0, 1, 100).reshape(1, -1)
gradient = np.vstack((gradient, gradient))
ax.imshow(gradient, extent=[0, 18, 0, 14], aspect='auto', alpha=0.05, cmap='Blues')

# 调整布局
plt.tight_layout()
plt.subplots_adjust(left=0.02, right=0.98, top=0.95, bottom=0.02)

# 保存图片
output_path = 'C:/手动D/行业实践/esp32_fire_alarm_architecture_complete.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight', 
            facecolor='white', edgecolor='none')

print(f"完整架构图已保存到: {output_path}")

# 显示图片
plt.show()