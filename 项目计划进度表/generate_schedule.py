import pandas as pd

def create_project_schedule():
    # 项目数据 - 根据ESP32宿舍火灾报警系统项目计划进度表.md
    projects = [
        '立项', '立项', '项目设计', '项目设计', '硬件设计', '硬件设计', '硬件设计', 
        '硬件设计', '硬件设计', '硬件设计', '硬件设计', '硬件设计', '硬件设计', 
        '软件设计', '软件设计', '软件设计', '软件设计', '硬件实现', '硬件实现', 
        '硬件实现', '硬件实现', '硬件实现', '硬件实现', '软件实现', '软件实现', 
        '软件实现', '软件实现', '软件实现', '系统测试', '系统测试', '系统测试', 
        '系统测试', '系统测试', '系统测试', '文档编写', '文档编写', '项目交付', 
        '项目交付'
    ]
    
    processes = [
        '项目启动', '项目启动', '方案设计', '方案设计', '器件选型', '原理图设计', 
        'PCB布局设计', 'BOM表制作', 'BOM表提交', 'PCB焊接组装', '传感器调试', 
        'ESP32烧录测试', '硬件功能测试', '硬件优化修改', '整体硬件调试', 
        '系统架构设计', '开发环境搭建', '数据库设计', 'API接口设计', '前端界面设计', 
        '后端框架搭建', 'API接口开发', '后端开发', '前端页面开发', '前后端联调', 
        '系统集成测试', '软件bug修复', '系统联调', '系统联调', '传感器校准', 
        '稳定性测试', '功耗测试', '硬件文档编写', '软件文档编写', '项目演示准备', 
        '项目演示准备', '项目答辩', '项目答辩', '算法优化', '性能优化'
    ]
    
    # 计算总行数
    total_rows = len(projects)
    
    # 创建日期数据
    dates_data = {}
    date_columns = ['9/7', '9/8', '9/9', '9/10', '9/11', '9/12', '9/13', '9/14', 
                   '9/15', '9/16', '9/17', '9/18', '9/19', '9/20', '9/21', 
                   '9/22', '9/23', '9/24', '9/25', '9/26', '9/27', '9/28']
    
    # 初始化所有日期列为空
    for date in date_columns:
        dates_data[date] = [''] * total_rows
    
    # 设置具体任务分配 - 根据ESP32项目计划进度表.md
    # 9/7: 项目启动
    dates_data['9/7'][0] = 'F'  # 立项-项目启动
    dates_data['9/7'][1] = 'A'  # 立项-项目启动
    
    # 9/12: 硬件方案设计 + 软件框架设计
    dates_data['9/12'][4] = 'F'  # 硬件设计-器件选型
    dates_data['9/12'][5] = 'A'  # 硬件设计-原理图设计
    
    # 9/13: 硬件设计 + 软件开发
    dates_data['9/13'][6] = 'F'  # 硬件设计-PCB布局设计
    dates_data['9/13'][7] = 'F'  # 硬件设计-BOM表制作
    dates_data['9/13'][15] = 'A'  # 软件设计-系统架构设计
    dates_data['9/13'][16] = 'A'  # 软件设计-开发环境搭建
    
    # 9/14: 硬件测试准备 + 软件前端设计
    dates_data['9/14'][8] = 'F'  # 硬件设计-BOM表提交
    dates_data['9/14'][9] = 'F'  # 硬件实现-PCB焊接组装
    dates_data['9/14'][17] = 'A'  # 软件设计-数据库设计
    dates_data['9/14'][18] = 'A'  # 软件设计-API接口设计
    dates_data['9/14'][19] = 'A'  # 软件实现-前端界面设计
    
    # 9/15: 硬件组装 + 软件后端开发
    dates_data['9/15'][10] = 'F'  # 硬件实现-传感器调试
    dates_data['9/15'][20] = 'A'  # 软件实现-后端框架搭建
    dates_data['9/15'][21] = 'A'  # 软件实现-API接口开发
    
    # 9/16: 软件模块开发
    dates_data['9/16'][22] = 'A'  # 软件实现-后端开发
    
    # 9/17: 硬件测试
    dates_data['9/17'][11] = 'F'  # 硬件实现-ESP32烧录测试
    dates_data['9/17'][12] = 'F'  # 硬件实现-硬件功能测试
    
    # 9/18: 硬件优化
    dates_data['9/18'][13] = 'F'  # 硬件实现-硬件优化修改
    dates_data['9/18'][23] = 'A'  # 软件实现-前端页面开发
    
    # 9/19: 硬件调试 + 软件联调
    dates_data['9/19'][14] = 'F'  # 硬件实现-整体硬件调试
    dates_data['9/19'][24] = 'A'  # 软件实现-前后端联调
    dates_data['9/19'][25] = 'A'  # 软件实现-系统集成测试
    
    # 9/20: 软件测试
    dates_data['9/20'][26] = 'A'  # 软件实现-软件bug修复
    
    # 9/21: 系统集成
    dates_data['9/21'][27] = 'F'  # 系统测试-系统联调
    dates_data['9/21'][28] = 'A'  # 系统测试-系统联调
    
    # 9/22: 无课
    
    # 9/23: 无课
    
    # 9/24: 无课
    
    # 9/25: 无课
    
    # 9/26: 无课
    
    # 9/27: 系统测试 + 文档编写
    dates_data['9/27'][29] = 'F'  # 系统测试-传感器校准
    dates_data['9/27'][30] = 'F'  # 系统测试-稳定性测试
    dates_data['9/27'][31] = 'F'  # 系统测试-功耗测试
    dates_data['9/27'][32] = 'F'  # 文档编写-硬件文档编写
    dates_data['9/27'][33] = 'A'  # 系统测试-算法优化
    dates_data['9/27'][34] = 'A'  # 系统测试-性能优化
    dates_data['9/27'][35] = 'A'  # 系统测试-用户体验优化
    dates_data['9/27'][36] = 'A'  # 文档编写-软件文档编写
    
    # 9/28: 项目交付
    if len(projects) > 37:
        dates_data['9/28'][37] = 'F'  # 文档编写-项目演示准备
    if len(projects) > 38:
        dates_data['9/28'][38] = 'A'  # 文档编写-项目演示准备
    if len(projects) > 39:
        dates_data['9/28'][39] = 'F'  # 项目交付-项目答辩
    if len(projects) > 40:
        dates_data['9/28'][40] = 'A'  # 项目交付-项目答辩
    
    data = {
        '项目': projects,
        '工序': processes,
        '时间': ['2024年9月'] * total_rows,
        **dates_data
    }
    
    # 调试：检查所有数组长度
    print("调试信息：")
    print(f"projects长度: {len(projects)}")
    print(f"processes长度: {len(processes)}")
    print(f"时间长度: {len(data['时间'])}")
    for key in dates_data:
        print(f"{key}长度: {len(dates_data[key])}")
    
    # 检查索引范围
    print(f"最大索引: {total_rows - 1}")
    
    # 创建DataFrame
    df = pd.DataFrame(data)
    
    # 保存到Excel
    try:
        with pd.ExcelWriter('项目计划进度表.xlsx', engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='项目进度', index=False)
            
            # 获取工作表对象
            worksheet = writer.sheets['项目进度']
            
            # 设置列宽
            column_widths = {
                'A': 15,  # 项目
                'B': 20,  # 工序
                'C': 12,  # 时间
                'D': 6,   # 9/7
                'E': 6,   # 9/8
                'F': 6,   # 9/9
                'G': 6,   # 9/10
                'H': 6,   # 9/11
                'I': 6,   # 9/12
                'J': 6,   # 9/13
                'K': 6,   # 9/14
                'L': 6,   # 9/15
                'M': 6,   # 9/16
                'N': 6,   # 9/17
                'O': 6,   # 9/18
                'P': 6,   # 9/19
                'Q': 6,   # 9/20
                'R': 6,   # 9/21
                'S': 6,   # 9/22
                'T': 6,   # 9/23
                'U': 6,   # 9/24
                'V': 6,   # 9/25
                'W': 6,   # 9/26
                'X': 6,   # 9/27
                'Y': 6,   # 9/28
            }
            
            for col, width in column_widths.items():
                worksheet.column_dimensions[col].width = width
            
            # 添加标题行
            title_row = ['项目进度表：（基于ESP32的宿舍火灾报警系统）', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '']
            worksheet.insert_rows(1)
            for col, value in enumerate(title_row, 1):
                worksheet.cell(row=1, column=col, value=value)
            
            # 添加时间行
            time_row = ['时间', '', '2024年9月', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '']
            worksheet.insert_rows(2)
            for col, value in enumerate(time_row, 1):
                worksheet.cell(row=2, column=col, value=value)
            
            # 添加日期行
            date_header = ['项目', '工序', '时间', '休', '休', '休', '休', '休', '休', '休', '休', '休', '休', '休', '休', '休', '休', '休', '休', '休', '休', '休', '休', '休', '休', '休', '休', '休']
            worksheet.insert_rows(3)
            for col, value in enumerate(date_header, 1):
                worksheet.cell(row=3, column=col, value=value)
            
            # 添加日期数字行
            date_numbers = ['', '', '', '日', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28']
            worksheet.insert_rows(4)
            for col, value in enumerate(date_numbers, 1):
                worksheet.cell(row=4, column=col, value=value)
            
            # 添加备注
            note_row = ['注意: F=硬件工程师, A=软件工程师, 空白=无课或无任务', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '']
            worksheet.insert_rows(len(df) + 6)
            for col, value in enumerate(note_row, 1):
                worksheet.cell(row=len(df) + 6, column=col, value=value)
        
        print("Excel文件 '项目计划进度表.xlsx' 已生成成功！")
        print("请在当前目录查看生成的Excel文件。")
        
    except Exception as e:
        print(f"生成Excel文件时出错: {e}")
        print("请确保已安装pandas和openpyxl库:")
        print("pip install pandas openpyxl")

if __name__ == "__main__":
    create_project_schedule()