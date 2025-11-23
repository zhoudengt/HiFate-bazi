#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交互式浏览器测试脚本 - 用户可以输入日期，浏览器保持打开以便观察和调试

使用方法:
  python interactive_browser_test.py
  python interactive_browser_test.py --date 1990-01-01 --time 12:00 --gender male
"""

import time
import json
import sys
import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class InteractiveBrowserTester:
    def __init__(self):
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """设置Chrome驱动"""
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        # 启用日志
        chrome_options.set_capability('goog:loggingPrefs', {'browser': 'ALL', 'performance': 'ALL'})
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            print("✅ Chrome浏览器已启动")
            return True
        except Exception as e:
            print(f"❌ 无法启动Chrome浏览器: {e}")
            print("请确保已安装Chrome浏览器和ChromeDriver")
            return False
    
    def get_console_logs(self):
        """获取浏览器控制台日志"""
        logs = []
        try:
            browser_logs = self.driver.get_log('browser')
            for log in browser_logs:
                logs.append({
                    'level': log['level'],
                    'message': log['message'],
                    'timestamp': log['timestamp']
                })
        except Exception as e:
            print(f"获取日志失败: {e}")
        return logs
    
    def execute_js(self, script):
        """执行JavaScript并返回结果"""
        try:
            return self.driver.execute_script(script)
        except Exception as e:
            print(f"执行JavaScript失败: {e}")
            return None
    
    def print_page_data(self):
        """打印当前页面数据"""
        print("\n" + "=" * 60)
        print("当前页面数据:")
        print("=" * 60)
        
        page_data = self.execute_js("""
            return {
                dayun: window.currentData?.dayun || null,
                liunian: window.currentData?.liunian || null,
                liuyue: window.currentData?.liuyue || null,
                selectedDayun: window.currentData?.selectedDayun || null,
                selectedLiunian: window.currentData?.selectedLiunian || null
            };
        """)
        
        if page_data:
            # 大运数据
            dayun = page_data.get('dayun')
            if dayun:
                dayun_list = dayun.get('list', [])
                print(f"\n📊 大运数据:")
                print(f"  总数: {len(dayun_list)}")
                if dayun_list:
                    print(f"\n  前5个大运:")
                    for i, d in enumerate(dayun_list[:5]):
                        year_range = d.get('year_range', {})
                        print(f"    [{i}] index={d.get('index')}, 年份: {year_range.get('start')}-{year_range.get('end')}, 干支: {d.get('ganzhi')}")
            
            # 选中的大运
            selected_dayun = page_data.get('selectedDayun')
            if selected_dayun:
                year_range = selected_dayun.get('year_range', {})
                print(f"\n✅ 选中的大运:")
                print(f"  index: {selected_dayun.get('index')}")
                print(f"  年份范围: {year_range.get('start')} - {year_range.get('end')}")
                print(f"  干支: {selected_dayun.get('ganzhi')}")
            else:
                print(f"\n❌ 未选中大运")
            
            # 流年数据
            liunian = page_data.get('liunian')
            if liunian:
                liunian_list = liunian.get('list', [])
                print(f"\n📊 流年数据:")
                print(f"  总数: {len(liunian_list)}")
                if liunian_list:
                    years = [item.get('year') for item in liunian_list if item.get('year')]
                    if years:
                        print(f"  年份范围: {min(years)} - {max(years)}")
                        print(f"  年份列表: {years[:10]}..." if len(years) > 10 else f"  年份列表: {years}")
            
            # 选中的流年
            selected_liunian = page_data.get('selectedLiunian')
            if selected_liunian:
                print(f"\n✅ 选中的流年:")
                print(f"  年份: {selected_liunian.get('year')}")
                print(f"  干支: {selected_liunian.get('ganzhi')}")
            else:
                print(f"\n❌ 未选中流年")
            
            # 流月数据
            liuyue = page_data.get('liuyue')
            if liuyue:
                liuyue_list = liuyue.get('list', [])
                print(f"\n📊 流月数据:")
                print(f"  总数: {len(liuyue_list)}")
            else:
                print(f"\n❌ 流月数据为空")
        
        print("=" * 60)
    
    def check_selected_styles(self):
        """检查选中样式（双重边框问题）"""
        print("\n" + "=" * 60)
        print("检查选中样式:")
        print("=" * 60)
        
        try:
            # 检查大运选中样式
            dayun_table = self.driver.find_element(By.ID, "dayunTable")
            selected_cells = dayun_table.find_elements(
                By.CSS_SELECTOR, 
                ".timeline-dayun-cell.timeline-selected"
            )
            print(f"\n大运选中单元格数量: {len(selected_cells)}")
            
            if len(selected_cells) > 0:
                for i, cell in enumerate(selected_cells):
                    styles = self.execute_js("""
                        var cell = arguments[0];
                        var computed = window.getComputedStyle(cell);
                        return {
                            border: computed.border,
                            borderWidth: computed.borderWidth,
                            borderColor: computed.borderColor,
                            borderStyle: computed.borderStyle,
                            boxShadow: computed.boxShadow
                        };
                    """, cell)
                    print(f"\n  选中单元格[{i}]样式:")
                    print(f"    border: {styles.get('border')}")
                    print(f"    borderWidth: {styles.get('borderWidth')}")
                    print(f"    borderColor: {styles.get('borderColor')}")
                    print(f"    boxShadow: {styles.get('boxShadow')}")
                    
                    # 检查是否有双重边框
                    border_width = styles.get('borderWidth', '')
                    if '2px' in border_width or '3px' in border_width or '4px' in border_width:
                        print(f"    ⚠️  可能有多重边框")
                    else:
                        print(f"    ✅ 边框正常")
            
            # 检查流年选中样式
            liunian_table = self.driver.find_element(By.ID, "liunianTable")
            selected_liunian_cells = liunian_table.find_elements(
                By.CSS_SELECTOR,
                ".timeline-liunian-cell.timeline-selected"
            )
            print(f"\n流年选中单元格数量: {len(selected_liunian_cells)}")
            
        except Exception as e:
            print(f"❌ 检查样式失败: {e}")
        
        print("=" * 60)
    
    def interactive_test(self, solar_date=None, solar_time=None, gender=None):
        """交互式测试"""
        print("=" * 60)
        print("交互式浏览器测试")
        print("=" * 60)
        
        if not self.driver:
            print("❌ 浏览器未启动，无法测试")
            return False
        
        try:
            # 打开fortune页面
            url = "http://127.0.0.1:8080/fortune.html"
            print(f"\n1. 打开页面: {url}")
            self.driver.get(url)
            time.sleep(2)
            
            # 等待页面加载
            wait = WebDriverWait(self.driver, 10)
            
            # 交互式输入（支持函数参数，如果没有则提示输入）
            print("\n" + "=" * 60)
            print("测试数据输入:")
            print("=" * 60)
            
            # 如果函数参数没有提供，尝试交互式输入
            if not solar_date:
                try:
                    solar_date = input("出生日期 (格式: YYYY-MM-DD，默认: 1990-01-01): ").strip()
                    if not solar_date:
                        solar_date = "1990-01-01"
                except (EOFError, KeyboardInterrupt):
                    solar_date = "1990-01-01"
                    print(f"使用默认日期: {solar_date}")
            
            if not solar_time:
                try:
                    solar_time = input("出生时间 (格式: HH:MM，默认: 12:00): ").strip()
                    if not solar_time:
                        solar_time = "12:00"
                except (EOFError, KeyboardInterrupt):
                    solar_time = "12:00"
                    print(f"使用默认时间: {solar_time}")
            
            if not gender:
                try:
                    gender = input("性别 (male/female，默认: male): ").strip()
                    if not gender:
                        gender = "male"
                except (EOFError, KeyboardInterrupt):
                    gender = "male"
                    print(f"使用默认性别: {gender}")
            
            print(f"\n✅ 使用测试数据: {solar_date} {solar_time} {gender}")
            
            # 输入数据
            print("\n2. 输入测试数据...")
            solar_date_input = wait.until(
                EC.presence_of_element_located((By.ID, "solar_date"))
            )
            solar_time_input = self.driver.find_element(By.ID, "solar_time")
            gender_select = self.driver.find_element(By.ID, "gender")
            
            # ✅ 修复：对于HTML5的type="date"和type="time"输入框，使用JavaScript设置值
            # 这样可以确保格式正确匹配
            print(f"  设置日期: {solar_date}")
            self.driver.execute_script(
                "arguments[0].value = arguments[1];",
                solar_date_input,
                solar_date
            )
            # 触发change事件，确保前端能检测到值的变化
            self.driver.execute_script(
                "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
                solar_date_input
            )
            
            print(f"  设置时间: {solar_time}")
            self.driver.execute_script(
                "arguments[0].value = arguments[1];",
                solar_time_input,
                solar_time
            )
            self.driver.execute_script(
                "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
                solar_time_input
            )
            
            print(f"  设置性别: {gender}")
            # 对于select，使用Select类更可靠
            from selenium.webdriver.support.ui import Select
            gender_select_obj = Select(gender_select)
            gender_select_obj.select_by_value(gender)
            
            # 验证输入的值
            actual_date = self.driver.execute_script("return arguments[0].value;", solar_date_input)
            actual_time = self.driver.execute_script("return arguments[0].value;", solar_time_input)
            actual_gender = self.driver.execute_script("return arguments[0].value;", gender_select)
            print(f"  ✅ 验证输入值:")
            print(f"    日期: {actual_date} (期望: {solar_date})")
            print(f"    时间: {actual_time} (期望: {solar_time})")
            print(f"    性别: {actual_gender} (期望: {gender})")
            
            if actual_date != solar_date:
                print(f"  ⚠️  日期不匹配！尝试使用send_keys方法...")
                solar_date_input.clear()
                solar_date_input.send_keys(solar_date)
                actual_date = self.driver.execute_script("return arguments[0].value;", solar_date_input)
                print(f"    重新设置后日期: {actual_date}")
            
            # 点击查询按钮
            print("\n3. 点击查询按钮...")
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_btn.click()
            print("✅ 已点击查询按钮")
            
            # 等待结果加载
            print("\n4. 等待结果加载（10秒）...")
            try:
                wait.until(EC.presence_of_element_located((By.ID, "dayunTable")))
                print("✅ 大运表格已出现")
            except TimeoutException:
                print("⚠️  大运表格未在10秒内出现")
            time.sleep(3)
            
            # 打印初始数据
            self.print_page_data()
            
            # 交互式操作
            print("\n" + "=" * 60)
            print("浏览器已打开，您可以:")
            print("  1. 手动点击大运/流年进行测试")
            print("  2. 在浏览器中打开开发者工具查看控制台")
            print("  3. 输入命令查看数据或检查样式")
            print("=" * 60)
            print("\n可用命令:")
            print("  'data' - 查看当前页面数据")
            print("  'style' - 检查选中样式（双重边框问题）")
            print("  'logs' - 查看控制台日志")
            print("  'quit' - 退出测试")
            print("=" * 60)
            
            # 交互式命令循环
            print("\n💡 提示: 浏览器会保持打开，您可以手动操作，然后输入命令查看结果")
            print("   按 Ctrl+C 退出测试\n")
            
            while True:
                try:
                    cmd = input("\n请输入命令 (data/style/logs/quit): ").strip().lower()
                    
                    if cmd == 'quit' or cmd == 'q':
                        print("退出测试...")
                        break
                    elif cmd == 'data' or cmd == 'd':
                        self.print_page_data()
                    elif cmd == 'style' or cmd == 's':
                        self.check_selected_styles()
                    elif cmd == 'logs' or cmd == 'l':
                        logs = self.get_console_logs()
                        print(f"\n控制台日志 (最近20条):")
                        for log in logs[-20:]:
                            level = log['level']
                            msg = log['message'][:200]
                            if 'error' in level.lower() or 'warning' in level.lower():
                                print(f"  [{level}] {msg}")
                    elif cmd == '':
                        # 空命令，刷新数据
                        self.print_page_data()
                    else:
                        print(f"未知命令: {cmd}")
                
                except (EOFError, KeyboardInterrupt):
                    print("\n\n用户中断，退出...")
                    break
                except Exception as e:
                    print(f"❌ 执行命令失败: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            print("\n关闭浏览器...")
            self.driver.quit()
            print("✅ 浏览器已关闭")

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='交互式浏览器测试')
    parser.add_argument('--date', type=str, default=None, help='出生日期 (YYYY-MM-DD)')
    parser.add_argument('--time', type=str, default=None, help='出生时间 (HH:MM)')
    parser.add_argument('--gender', type=str, default=None, choices=['male', 'female'], help='性别')
    args = parser.parse_args()
    
    tester = InteractiveBrowserTester()
    if tester.driver:
        try:
            tester.interactive_test(
                solar_date=args.date,
                solar_time=args.time,
                gender=args.gender
            )
        except KeyboardInterrupt:
            print("\n用户中断")
        finally:
            tester.close()
    else:
        print("无法启动浏览器，请检查Chrome和ChromeDriver安装")

