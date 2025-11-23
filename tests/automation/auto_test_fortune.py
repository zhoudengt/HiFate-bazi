#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化测试脚本 - 自动测试大运流年功能，检查双重边框和年份匹配问题
"""

import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException

class AutoTester:
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
        chrome_options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            print("✅ Chrome浏览器已启动")
            return True
        except Exception as e:
            print(f"❌ 无法启动Chrome浏览器: {e}")
            return False
    
    def execute_js(self, script, *args):
        """执行JavaScript并返回结果"""
        try:
            return self.driver.execute_script(script, *args)
        except Exception as e:
            print(f"执行JavaScript失败: {e}")
            return None
    
    def get_page_data(self):
        """获取页面数据"""
        return self.execute_js("""
            return {
                dayun: window.currentData?.dayun || null,
                liunian: window.currentData?.liunian || null,
                liuyue: window.currentData?.liuyue || null,
                selectedDayun: window.currentData?.selectedDayun || null,
                selectedLiunian: window.currentData?.selectedLiunian || null
            };
        """)
    
    def check_selected_styles(self, table_id, cell_class):
        """检查选中样式"""
        try:
            table = self.driver.find_element(By.ID, table_id)
            selected_cells = table.find_elements(By.CSS_SELECTOR, f".{cell_class}.timeline-selected")
            
            if len(selected_cells) > 1:
                print(f"  ❌ 发现 {len(selected_cells)} 个选中单元格（应该有且仅有1个）")
                return False
            elif len(selected_cells) == 1:
                cell = selected_cells[0]
                styles = self.execute_js("""
                    var cell = arguments[0];
                    var computed = window.getComputedStyle(cell);
                    return {
                        borderWidth: computed.borderWidth,
                        borderColor: computed.borderColor,
                        borderStyle: computed.borderStyle
                    };
                """, cell)
                
                border_width = styles.get('borderWidth', '')
                # 检查是否有双重边框（borderWidth可能包含多个值）
                if '2px' in border_width or '3px' in border_width or '4px' in border_width:
                    # 检查是否有多个边框值（双重边框的特征）
                    parts = border_width.split()
                    if len(parts) > 1:
                        print(f"  ⚠️  可能有多重边框: {border_width}")
                        return False
                    else:
                        print(f"  ✅ 边框正常: {border_width}")
                        return True
                else:
                    print(f"  ✅ 边框正常: {border_width}")
                    return True
            else:
                print(f"  ⚠️  未找到选中单元格")
                return False
        except Exception as e:
            print(f"  ❌ 检查样式失败: {e}")
            return False
    
    def click_dayun_by_data_index(self, dayun_data_index):
        """点击指定data-dayun-index的大运"""
        try:
            # 查找大运表格
            dayun_table = self.driver.find_element(By.ID, "dayunTable")
            
            # ✅ 修复：使用data-dayun-index属性查找，而不是数组索引
            cell = dayun_table.find_element(By.CSS_SELECTOR, f".timeline-dayun-cell[data-dayun-index='{dayun_data_index}']")
            
            # 获取大运信息
            cell_info = self.execute_js("""
                var cell = arguments[0];
                return {
                    text: cell.textContent,
                    classes: cell.className,
                    index: cell.getAttribute('data-dayun-index')
                };
            """, cell)
            
            print(f"  点击大运[data-index={dayun_data_index}]: {cell_info.get('text', '')[:50]}")
            
            # 滚动到元素
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cell)
            time.sleep(0.5)
            
            # 点击
            cell.click()
            time.sleep(2)  # 等待数据加载
            
            return True
        except Exception as e:
            print(f"  ❌ 点击大运失败: {e}")
            return False
    
    def get_all_dayun_indices(self):
        """获取所有大运的data-dayun-index值"""
        try:
            dayun_table = self.driver.find_element(By.ID, "dayunTable")
            all_cells = dayun_table.find_elements(By.CSS_SELECTOR, ".timeline-dayun-cell.timeline-clickable")
            
            indices = []
            for cell in all_cells:
                if '小运' not in cell.text:
                    data_index = self.execute_js("return arguments[0].getAttribute('data-dayun-index');", cell)
                    if data_index:
                        indices.append(int(data_index))
            
            return sorted(set(indices))  # 去重并排序
        except Exception as e:
            print(f"获取大运索引失败: {e}")
            return []
    
    def test(self, solar_date="1990-01-01", solar_time="12:00", gender="male"):
        """运行测试"""
        print("=" * 60)
        print("自动化测试 - 大运流年功能")
        print("=" * 60)
        
        if not self.driver:
            print("❌ 浏览器未启动")
            return False
        
        try:
            # 打开页面
            print(f"\n1. 打开页面: http://127.0.0.1:8080/fortune.html")
            self.driver.get("http://127.0.0.1:8080/fortune.html")
            time.sleep(2)
            
            wait = WebDriverWait(self.driver, 10)
            
            # 输入数据
            print(f"\n2. 输入测试数据: {solar_date} {solar_time} {gender}")
            solar_date_input = wait.until(EC.presence_of_element_located((By.ID, "solar_date")))
            solar_time_input = self.driver.find_element(By.ID, "solar_time")
            gender_select = self.driver.find_element(By.ID, "gender")
            
            self.driver.execute_script("arguments[0].value = arguments[1];", solar_date_input, solar_date)
            self.driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", solar_date_input)
            
            self.driver.execute_script("arguments[0].value = arguments[1];", solar_time_input, solar_time)
            self.driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", solar_time_input)
            
            Select(gender_select).select_by_value(gender)
            
            # 提交表单
            print("\n3. 提交表单...")
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_btn.click()
            
            # 等待结果
            print("\n4. 等待结果加载...")
            wait.until(EC.presence_of_element_located((By.ID, "dayunTable")))
            time.sleep(3)
            
            # 获取初始数据
            print("\n5. 获取初始数据...")
            initial_data = self.get_page_data()
            dayun_list = initial_data.get('dayun', {}).get('list', [])
            print(f"  大运总数: {len(dayun_list)}")
            
            if len(dayun_list) < 2:
                print("  ❌ 大运数据不足，无法测试")
                return False
            
            # 测试1: 检查初始状态的选中样式（双重边框问题）
            print("\n" + "=" * 60)
            print("测试1: 检查初始选中样式（双重边框问题）")
            print("=" * 60)
            
            initial_selected = initial_data.get('selectedDayun')
            if initial_selected:
                print(f"  初始选中大运: index={initial_selected.get('index')}, 年份={initial_selected.get('year_range', {}).get('start')}-{initial_selected.get('year_range', {}).get('end')}")
            
            style_ok = self.check_selected_styles("dayunTable", "timeline-dayun-cell")
            if style_ok:
                print("  ✅ 大运选中样式正常（无双重边框）")
            else:
                print("  ❌ 大运选中样式异常（可能有双重边框）")
            
            # 测试2: 点击不同的大运，检查流年范围
            print("\n" + "=" * 60)
            print("测试2: 点击大运，检查流年范围匹配")
            print("=" * 60)
            
            # ✅ 修复：获取所有大运的data-dayun-index值
            all_indices = self.get_all_dayun_indices()
            print(f"  找到的大运索引: {all_indices}")
            
            # 测试前3个大运（排除第一个，因为可能是小运）
            test_indices = all_indices[1:4] if len(all_indices) > 3 else all_indices[1:3]
            
            for data_index in test_indices:
                # 从dayun_list中找到对应的大运
                dayun = next((d for d in dayun_list if d.get('index') == data_index), None)
                if not dayun:
                    print(f"\n  ⚠️  找不到索引为 {data_index} 的大运")
                    continue
                
                expected_start = dayun.get('year_range', {}).get('start')
                expected_end = dayun.get('year_range', {}).get('end')
                
                print(f"\n  测试大运[data-index={data_index}]: 期望流年范围 {expected_start}-{expected_end}")
                
                # 点击大运（使用data-dayun-index）
                if not self.click_dayun_by_data_index(data_index):
                    continue
                
                # 获取点击后的数据
                after_click_data = self.get_page_data()
                selected_dayun = after_click_data.get('selectedDayun')
                liunian_list = after_click_data.get('liunian', {}).get('list', [])
                
                if selected_dayun:
                    actual_start = selected_dayun.get('year_range', {}).get('start')
                    actual_end = selected_dayun.get('year_range', {}).get('end')
                    print(f"    选中大运: {actual_start}-{actual_end}")
                
                if liunian_list:
                    years = [item.get('year') for item in liunian_list if item.get('year')]
                    if years:
                        liunian_start = min(years)
                        liunian_end = max(years)
                        print(f"    实际流年范围: {liunian_start}-{liunian_end}")
                        
                        # 验证范围是否匹配
                        if liunian_start == expected_start and liunian_end == expected_end:
                            print(f"    ✅ 流年范围匹配！")
                        else:
                            print(f"    ❌ 流年范围不匹配！")
                            print(f"      期望: {expected_start}-{expected_end}")
                            print(f"      实际: {liunian_start}-{liunian_end}")
                else:
                    print(f"    ❌ 流年数据为空")
                
                # 检查选中样式
                style_ok = self.check_selected_styles("dayunTable", "timeline-dayun-cell")
                if not style_ok:
                    print(f"    ❌ 选中样式异常（可能有双重边框）")
                
                time.sleep(1)
            
            # 测试3: 检查流年选中样式
            print("\n" + "=" * 60)
            print("测试3: 检查流年选中样式")
            print("=" * 60)
            
            style_ok = self.check_selected_styles("liunianTable", "timeline-liunian-cell")
            if style_ok:
                print("  ✅ 流年选中样式正常（无双重边框）")
            else:
                print("  ❌ 流年选中样式异常（可能有双重边框）")
            
            print("\n" + "=" * 60)
            print("测试完成！")
            print("=" * 60)
            print("\n浏览器将保持打开10秒，请查看...")
            time.sleep(10)
            
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
    tester = AutoTester()
    if tester.driver:
        try:
            tester.test()
        except KeyboardInterrupt:
            print("\n用户中断")
        finally:
            tester.close()
    else:
        print("无法启动浏览器")

