#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
浏览器自动化测试脚本 - 自动测试大运流年功能
使用 Selenium 自动操作浏览器并捕获调试信息
"""

import time
import json
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class BrowserTester:
    def __init__(self):
        self.driver = None
        self.console_logs = []
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
            print("安装方法: brew install chromedriver (macOS)")
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
    
    def test_fortune_page(self):
        """测试fortune页面"""
        print("=" * 60)
        print("开始浏览器自动化测试")
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
            
            # 输入测试数据
            print("\n2. 输入测试数据...")
            solar_date_input = wait.until(
                EC.presence_of_element_located((By.ID, "solar_date"))
            )
            solar_time_input = self.driver.find_element(By.ID, "solar_time")
            gender_select = self.driver.find_element(By.ID, "gender")
            
            solar_date_input.clear()
            solar_date_input.send_keys("1990-01-01")
            
            solar_time_input.clear()
            solar_time_input.send_keys("12:00")
            
            gender_select.send_keys("male")
            
            print("✅ 已输入测试数据: 1990-01-01 12:00 男")
            
            # 点击查询按钮
            print("\n3. 点击查询按钮...")
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_btn.click()
            print("✅ 已点击查询按钮")
            
            # 等待结果加载
            print("\n4. 等待结果加载...")
            # 等待表格出现
            try:
                wait.until(EC.presence_of_element_located((By.ID, "dayunTable")))
                print("✅ 大运表格已出现")
            except TimeoutException:
                print("⚠️  大运表格未在10秒内出现")
            time.sleep(3)  # 额外等待数据渲染
            
            # 获取页面数据
            print("\n5. 获取页面数据...")
            page_data = self.execute_js("""
                return {
                    dayun: window.currentData?.dayun || null,
                    liunian: window.currentData?.liunian || null,
                    liuyue: window.currentData?.liuyue || null,
                    selectedDayun: window.currentData?.selectedDayun || null
                };
            """)
            
            if page_data and page_data.get('dayun'):
                print("\n页面数据:")
                dayun_list = page_data.get('dayun', {}).get('list', [])
                print(f"  大运数量: {len(dayun_list)}")
                
                if dayun_list:
                    print("\n前3个大运:")
                    for i, dayun in enumerate(dayun_list[:3]):
                        year_range = dayun.get('year_range', {})
                        print(f"  {i+1}. index={dayun.get('index')}, 年份范围: {year_range.get('start')}-{year_range.get('end')}, 干支: {dayun.get('ganzhi')}")
                
                liunian_list = page_data.get('liunian', {}).get('list', [])
                print(f"\n  流年数量: {len(liunian_list)}")
                if liunian_list:
                    years = [item.get('year') for item in liunian_list if item.get('year')]
                    if years:
                        print(f"  流年年份范围: {min(years)} - {max(years)}")
                        print(f"  流年列表: {years}")
            
            # 查找大运表格
            print("\n6. 查找大运表格...")
            try:
                dayun_table = wait.until(
                    EC.presence_of_element_located((By.ID, "dayunTable"))
                )
                print("✅ 找到大运表格")
                
                # 调试：检查表格内容
                table_html = dayun_table.get_attribute('innerHTML')
                print(f"  表格HTML长度: {len(table_html)}")
                
                # 查找所有可能的单元格
                all_cells_by_class = dayun_table.find_elements(By.CSS_SELECTOR, ".timeline-dayun-cell")
                print(f"  找到 {len(all_cells_by_class)} 个 .timeline-dayun-cell 元素")
                
                clickable_cells = dayun_table.find_elements(By.CSS_SELECTOR, ".timeline-clickable")
                print(f"  找到 {len(clickable_cells)} 个 .timeline-clickable 元素")
                
                # 查找可点击的大运单元格（排除小运）
                # 注意：Selenium不支持:has()伪类，所以先获取所有单元格，然后过滤
                all_cells = dayun_table.find_elements(By.CSS_SELECTOR, ".timeline-dayun-cell.timeline-clickable")
                print(f"  找到 {len(all_cells)} 个同时具有两个类的元素")
                
                # 过滤掉小运
                dayun_cells = [cell for cell in all_cells if '小运' not in cell.text]
                
                # 如果还是找不到，尝试其他方式
                if len(dayun_cells) == 0:
                    # 尝试查找所有td元素
                    all_tds = dayun_table.find_elements(By.TAG_NAME, "td")
                    print(f"  找到 {len(all_tds)} 个td元素")
                    for i, td in enumerate(all_tds[:5]):  # 只显示前5个
                        classes = td.get_attribute('class')
                        text = td.text[:50]
                        print(f"    td[{i}]: class='{classes}', text='{text}'")
                
                print(f"  最终找到 {len(dayun_cells)} 个大运单元格（排除小运）")
                
                if len(dayun_cells) > 0:
                    # 点击第一个大运
                    print("\n7. 点击第一个大运...")
                    first_cell = dayun_cells[0]
                    
                    # 获取大运信息
                    dayun_info = self.execute_js("""
                        var cell = arguments[0];
                        var index = cell.getAttribute('data-dayun-index');
                        return {
                            index: index,
                            text: cell.textContent,
                            classes: cell.className
                        };
                    """, first_cell)
                    
                    print(f"  大运信息: {json.dumps(dayun_info, indent=2, ensure_ascii=False)}")
                    
                    # 滚动到元素
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", first_cell)
                    time.sleep(1)
                    
                    # 点击
                    first_cell.click()
                    print("✅ 已点击第一个大运")
                    
                    # 等待流年加载
                    print("\n8. 等待流年加载...")
                    time.sleep(3)
                    
                    # 获取点击后的数据
                    print("\n9. 获取点击后的数据...")
                    after_click_data = self.execute_js("""
                        return {
                            selectedDayun: window.currentData?.selectedDayun,
                            liunian: window.currentData?.liunian,
                            liuyue: window.currentData?.liuyue
                        };
                    """)
                    
                    if after_click_data:
                        selected_dayun = after_click_data.get('selectedDayun')
                        if selected_dayun:
                            year_range = selected_dayun.get('year_range', {})
                            print(f"\n  选中的大运:")
                            print(f"    index: {selected_dayun.get('index')}")
                            print(f"    年份范围: {year_range.get('start')} - {year_range.get('end')}")
                            print(f"    干支: {selected_dayun.get('ganzhi')}")
                        
                        liunian_list = after_click_data.get('liunian', {}).get('list', [])
                        print(f"\n  点击后流年数量: {len(liunian_list)}")
                        if liunian_list:
                            years = [item.get('year') for item in liunian_list if item.get('year')]
                            if years:
                                min_year = min(years)
                                max_year = max(years)
                                print(f"  点击后流年年份范围: {min_year} - {max_year}")
                                
                                # 验证年份范围
                                if selected_dayun:
                                    expected_start = year_range.get('start')
                                    expected_end = year_range.get('end')
                                    if min_year == expected_start and max_year == expected_end:
                                        print(f"  ✅ 流年范围匹配！")
                                    else:
                                        print(f"  ❌ 流年范围不匹配！")
                                        print(f"    期望: {expected_start} - {expected_end}")
                                        print(f"    实际: {min_year} - {max_year}")
                        
                        liuyue_list = after_click_data.get('liuyue', {}).get('list', [])
                        print(f"\n  点击后流月数量: {len(liuyue_list)}")
                        if liuyue_list:
                            print(f"  ✅ 流月数据已加载")
                        else:
                            print(f"  ❌ 流月数据为空")
                    
                    # 检查选中样式（双重边框问题）
                    print("\n10. 检查选中样式...")
                    selected_cells = dayun_table.find_elements(
                        By.CSS_SELECTOR, 
                        ".timeline-dayun-cell.timeline-selected"
                    )
                    print(f"  选中的大运单元格数量: {len(selected_cells)}")
                    
                    if len(selected_cells) > 0:
                        first_selected = selected_cells[0]
                        styles = self.execute_js("""
                            var cell = arguments[0];
                            var computed = window.getComputedStyle(cell);
                            return {
                                border: computed.border,
                                borderWidth: computed.borderWidth,
                                borderColor: computed.borderColor,
                                borderStyle: computed.borderStyle
                            };
                        """, first_selected)
                        print(f"  选中单元格样式: {json.dumps(styles, indent=2, ensure_ascii=False)}")
                        
                        # 检查是否有双重边框
                        border_width = styles.get('borderWidth', '')
                        if '2px' in border_width or '3px' in border_width or '4px' in border_width:
                            print(f"  ⚠️  可能有多重边框（borderWidth: {border_width}）")
                        else:
                            print(f"  ✅ 边框正常")
                    
                    # 获取控制台日志
                    print("\n11. 获取控制台日志...")
                    console_logs = self.get_console_logs()
                    if console_logs:
                        print(f"  控制台日志数量: {len(console_logs)}")
                        # 只显示最近的日志
                        for log in console_logs[-10:]:
                            if 'error' in log['level'].lower() or 'warning' in log['level'].lower():
                                print(f"    [{log['level']}] {log['message'][:200]}")
                else:
                    print("❌ 未找到可点击的大运单元格")
                    
            except TimeoutException:
                print("❌ 超时：未找到大运表格")
            except Exception as e:
                print(f"❌ 查找大运表格失败: {e}")
                import traceback
                traceback.print_exc()
            
            # 保持浏览器打开一段时间，方便查看
            print("\n" + "=" * 60)
            print("测试完成！浏览器将保持打开30秒，请查看...")
            print("=" * 60)
            time.sleep(30)
            
            return True
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            print("✅ 浏览器已关闭")

if __name__ == "__main__":
    tester = BrowserTester()
    if tester.driver:
        try:
            tester.test_fortune_page()
        except KeyboardInterrupt:
            print("\n用户中断")
        finally:
            tester.close()
    else:
        print("无法启动浏览器，请检查Chrome和ChromeDriver安装")

