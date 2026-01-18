"""算命规则分析器"""

from core.config.fortune_rules_config import *
from core.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS

class FortuneRulesAnalyzer:
    """算命规则分析器"""

    def __init__(self, bazi_pillars, details, gender):
        self.bazi_pillars = bazi_pillars
        self.details = details
        self.gender = gender
        self.day_stem = bazi_pillars['day']['stem']
        self.day_branch = bazi_pillars['day']['branch']

    def analyze_all_rules(self):
        """分析所有算命规则"""
        rules_result = {}

        # 二、身材容貌
        rules_result['身材容貌'] = self._analyze_appearance()

        # 三、兄弟姐妹情况
        rules_result['兄弟姐妹情况'] = self._analyze_siblings_status()

        # 四、兄弟姐妹排行
        rules_result['兄弟姐妹排行'] = self._analyze_siblings_rank()

        # 五、兄弟姐妹个数
        rules_result['兄弟姐妹个数'] = self._analyze_siblings_count()

        # 六、破相疤痕
        rules_result['破相疤痕'] = self._analyze_scars()

        # 七、论官非刑狱
        rules_result['官非刑狱'] = self._analyze_law_trouble()

        # 八、破大财
        rules_result['破大财'] = self._analyze_financial_loss()

        # 九、头胎生男或女
        rules_result['头胎性别'] = self._analyze_first_child_gender()

        # 十、论离婚
        rules_result['离婚情况'] = self._analyze_divorce()

        # 十一、婚姻
        rules_result['婚姻状况'] = self._analyze_marriage()

        # 十二、论克丧偶
        rules_result['克丧偶'] = self._analyze_spouse_loss()

        # 十三、论配偶身材容貌
        rules_result['配偶容貌'] = self._analyze_spouse_appearance()

        # 十四、论夫妻看见大或小
        rules_result['婚恋早晚'] = self._analyze_marriage_timing()

        # 十五、子女情况
        rules_result['子女情况'] = self._analyze_children()

        # 十六、克害子女
        rules_result['克害子女'] = self._analyze_children_harm()

        # 十七、带眼镜之人
        rules_result['戴眼镜'] = self._analyze_glasses()

        # 十八、他乡谋生立业
        rules_result['他乡谋生'] = self._analyze_away_home()

        # 十九、命主阳宅
        rules_result['阳宅方位'] = self._analyze_house_direction()

        # 二十、寿命
        rules_result['寿命情况'] = self._analyze_lifespan()

        # 二十一、有惊无险之人
        rules_result['有惊无险'] = self._analyze_near_miss()

        # 二十二、病痛
        rules_result['病痛情况'] = self._analyze_illness()

        return rules_result

    def _analyze_appearance(self):
        """二、身材容貌"""
        year_pillar = f"{self.bazi_pillars['year']['stem']}{self.bazi_pillars['year']['branch']}"

        if self.gender == 'male':
            if year_pillar in MALE_HANDSOME_PILLARS:
                return f"年柱{year_pillar}在美貌列表{MALE_HANDSOME_PILLARS}中，命主容貌俊美"
            else:
                return f"年柱{year_pillar}不在美貌列表{MALE_HANDSOME_PILLARS}中"
        else:
            if year_pillar in FEMALE_HANDSOME_PILLARS:
                return f"年柱{year_pillar}在美貌列表{FEMALE_HANDSOME_PILLARS}中，命主容貌秀美"
            else:
                return f"年柱{year_pillar}不在美貌列表{FEMALE_HANDSOME_PILLARS}中"

    def _analyze_siblings_status(self):
        """三、兄弟姐妹情况"""
        year_main_star = self.details['year']['main_star']
        month_main_star = self.details['month']['main_star']
        hour_main_star = self.details['hour']['main_star']

        result = []

        # 年干主星见到正财、正官、偏印、比肩 排行不是老大
        if year_main_star in NOT_FIRST_RANK_STARS:
            result.append(f"年干主星{year_main_star}在{NOT_FIRST_RANK_STARS}中，排行不是老大")

        # 年干、月干、时干主星见到偏印，有兄弟姐妹婚姻不顺，或破相，并且本人小时候有灾难
        partial_star_stems = []
        if year_main_star == '偏印':
            partial_star_stems.append('年干')
        if month_main_star == '偏印':
            partial_star_stems.append('月干')
        if hour_main_star == '偏印':
            partial_star_stems.append('时干')

        if partial_star_stems:
            result.append(f"{'、'.join(partial_star_stems)}主星为偏印，兄弟姐妹婚姻不顺或破相，本人小时候有灾难")

        return "；".join(result) if result else "无特殊兄弟姐妹情况"

    def _analyze_siblings_rank(self):
        """四、兄弟姐妹排行"""
        hour_branch = self.bazi_pillars['hour']['branch']

        for rank, branches in RANK_BRANCHES.items():
            if hour_branch in branches:
                return f"时支{hour_branch}在{','.join(branches)}中，排行{rank}"

        return "排行情况不明确"

    def _analyze_siblings_count(self):
        """五、兄弟姐妹个数"""
        hour_branch = self.bazi_pillars['hour']['branch']

        count = SIBLINGS_COUNT_BRANCHES.get(hour_branch)
        if count:
            if hour_branch in ['辰', '戌', '丑', '未']:
                return f"时支{hour_branch}在辰戌丑未中，{count}个兄弟姐妹，年龄差3岁左右"
            else:
                return f"时支{hour_branch}，{count}个兄弟姐妹"

        return "兄弟姐妹个数不明确"

    def _analyze_scars(self):
        """六、破相疤痕"""
        year_main_star = self.details['year']['main_star']
        hour_main_star = self.details['hour']['main_star']

        # 检查年干和时干主星见劫财
        has_rob_wealth = year_main_star == '劫财' or hour_main_star == '劫财'

        # 检查地支见辰、午、酉
        branches = [
            self.bazi_pillars['year']['branch'],
            self.bazi_pillars['month']['branch'],
            self.bazi_pillars['day']['branch'],
            self.bazi_pillars['hour']['branch']
        ]

        scar_branches = [b for b in branches if b in SCAR_BRANCHES]
        knife_scar_branches = [b for b in branches if b in KNIFE_SCAR_BRANCHES]

        result = []
        if has_rob_wealth and scar_branches:
            result.append(f"年干/时干主星见劫财，地支见{scar_branches}，可能破相或有疤痕")

        if knife_scar_branches:
            result.append(f"地支见{knife_scar_branches}，可能有刀伤疤痕")

        return "；".join(result) if result else "无明显破相疤痕特征"

    def _analyze_law_trouble(self):
        """七、论官非刑狱"""
        day_stem = self.day_stem
        hour_stem = self.bazi_pillars['hour']['stem']

        # 检查日干、时干见戊
        has_wu_stem = day_stem == '戊' or hour_stem == '戊'

        # 检查地支见亥、子、辰、戌
        branches = [
            self.bazi_pillars['year']['branch'],
            self.bazi_pillars['month']['branch'],
            self.bazi_pillars['day']['branch'],
            self.bazi_pillars['hour']['branch']
        ]

        law_branches = [b for b in branches if b in LAW_TROUBLE_BRANCHES]

        if has_wu_stem and law_branches:
            return f"日干/时干见戊，地支见{law_branches}，20-36岁间可能惹官非牢狱"
        else:
            return "无明显官非刑狱特征"

    def _analyze_financial_loss(self):
        """八、破大财"""
        day_branch = self.day_branch

        if day_branch in FINANCIAL_LOSS_BRANCHES:
            return f"日支{day_branch}在{FINANCIAL_LOSS_BRANCHES}中，容易破大财，发财大起大落"
        else:
            return f"日支{day_branch}不在破财地支{FINANCIAL_LOSS_BRANCHES}中"

    def _analyze_first_child_gender(self):
        """九、头胎生男或女"""
        day_stem = self.day_stem
        hour_stem = self.bazi_pillars['hour']['stem']

        day_element = STEM_ELEMENTS[day_stem]
        hour_element = STEM_ELEMENTS[hour_stem]

        # 时干日干同五行头胎为男
        if day_element == hour_element:
            return f"日干{day_stem}({day_element})与时干{hour_stem}({hour_element})同五行，头胎为男"

        # 时干五行相生日干头胎为男
        element_relations = {
            '木': '火', '火': '土', '土': '金', '金': '水', '水': '木'
        }
        if element_relations.get(hour_element) == day_element:
            return f"时干{hour_stem}({hour_element})生日干{day_stem}({day_element})，头胎为男"

        # 男命时干五行相克日干头胎为男
        element_controls = {
            '木': '土', '火': '金', '土': '水', '金': '木', '水': '火'
        }
        if self.gender == 'male' and element_controls.get(hour_element) == day_element:
            return f"男命时干{hour_stem}({hour_element})克日干{day_stem}({day_element})，头胎为男"

        # 女命日干五行相克时干头胎为男
        if self.gender == 'female' and element_controls.get(day_element) == hour_element:
            return f"女命日干{day_stem}({day_element})克时干{hour_stem}({hour_element})，头胎为男"

        return "头胎为女"

    def _analyze_divorce(self):
        """十、论离婚"""
        day_main_star = self.details['day']['main_star']

        # 日干主星见劫财、七杀、伤官、偏印者婚姻不顺
        has_divorce_star = day_main_star in DIVORCE_STARS

        result = []
        if has_divorce_star:
            result.append(f"日干主星{day_main_star}在{DIVORCE_STARS}中，婚姻不顺")

        # 检查六合关系
        day_branch = self.day_branch
        other_branches = [
            self.bazi_pillars['year']['branch'],
            self.bazi_pillars['month']['branch'],
            self.bazi_pillars['hour']['branch']
        ]

        six_combine_branches = []
        for branch in other_branches:
            if SIX_HARMONIES.get(day_branch) == branch:
                six_combine_branches.append(branch)

        if six_combine_branches:
            result.append(f"日支{day_branch}与{','.join(six_combine_branches)}有六合关系，易有外遇或离婚")

        return "；".join(result) if result else "无明显离婚特征"

    def _analyze_marriage(self):
        """十一、婚姻"""
        day_branch = self.day_branch
        month_branch = self.bazi_pillars['month']['branch']
        year_branch = self.bazi_pillars['year']['branch']

        result = []

        # 日支月支是三刑或六冲，夫妻难沟通
        if (day_branch in THREE_PENALTIES.get(month_branch, []) or
                month_branch in THREE_PENALTIES.get(day_branch, []) or
                SIX_CONFLICTS.get(day_branch) == month_branch):
            result.append(f"日支{day_branch}与月支{month_branch}有三刑六冲，夫妻难沟通")

        # 女命日干主星是伤官或偏印或日干五行克日支五行，好骂丈夫
        if self.gender == 'female':
            day_main_star = self.details['day']['main_star']
            day_stem_element = STEM_ELEMENTS[self.day_stem]
            day_branch_element = BRANCH_ELEMENTS[day_branch]

            element_controls = {'木': '土', '火': '金', '土': '水', '金': '木', '水': '火'}
            if (day_main_star in ['伤官', '偏印'] or
                    element_controls.get(day_stem_element) == day_branch_element):
                result.append("女命好骂丈夫")

        return "；".join(result) if result else "婚姻状况相对平稳"

    def _analyze_spouse_loss(self):
        """十二、论克丧偶"""
        stems = [
            self.bazi_pillars['year']['stem'],
            self.bazi_pillars['month']['stem'],
            self.bazi_pillars['day']['stem'],
            self.bazi_pillars['hour']['stem']
        ]

        branches = [
            self.bazi_pillars['year']['branch'],
            self.bazi_pillars['month']['branch'],
            self.bazi_pillars['day']['branch'],
            self.bazi_pillars['hour']['branch']
        ]

        # 天干有甲、丁、戊、庚其中一字，地支又有辰、午、酉、亥其中一字，克配偶
        has_special_stems = any(stem in SPOUSE_LOSS_STEMS for stem in stems)
        has_special_branches = any(branch in SPOUSE_LOSS_BRANCHES for branch in branches)

        result = []
        if has_special_stems and has_special_branches:
            result.append("天干见甲丁戊庚，地支见辰午酉亥，克配偶")

        # 日支是辰、午、酉、亥其中一字，月支或时支是辰、午、酉、亥其中一字
        day_branch = self.day_branch
        month_branch = self.bazi_pillars['month']['branch']
        hour_branch = self.bazi_pillars['hour']['branch']

        if (day_branch in SPOUSE_LOSS_BRANCHES and
                (month_branch in SPOUSE_LOSS_BRANCHES or hour_branch in SPOUSE_LOSS_BRANCHES)):
            result.append("日支与月支/时支同见辰午酉亥，配偶38-48岁间可能离开")

        # 日支为辰、戌、丑、未其中一字
        if day_branch in ['辰', '戌', '丑', '未']:
            result.append("日支为辰戌丑未，配偶38-48岁间情感问题增多")

        return "；".join(result) if result else "无明显克丧偶特征"

    def _analyze_spouse_appearance(self):
        """十三、论配偶身材容貌"""
        day_branch = self.day_branch

        if self.gender == 'male':
            # 男日支：子、午、卯、酉妻貌美
            if day_branch in ['子', '午', '卯', '酉']:
                return f"男命日支{day_branch}在子午卯酉中，妻子貌美"
        else:
            # 女日支：子、午、卯、酉夫貌美
            if day_branch in ['子', '午', '卯', '酉']:
                return f"女命日支{day_branch}在子午卯酉中，丈夫貌美"

        # 日柱的天干和地支五行相生配偶不是高大就是肥胖
        day_stem_element = STEM_ELEMENTS[self.day_stem]
        day_branch_element = BRANCH_ELEMENTS[day_branch]

        element_produces = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
        if element_produces.get(day_stem_element) == day_branch_element:
            return f"日干{self.day_stem}({day_stem_element})生日支{day_branch}({day_branch_element})，配偶高大或肥胖"

        # 日柱天干地支相克，配偶瘦或小
        element_controls = {'木': '土', '火': '金', '土': '水', '金': '木', '水': '火'}
        if element_controls.get(day_stem_element) == day_branch_element:
            return f"日干{self.day_stem}({day_stem_element})克日支{day_branch}({day_branch_element})，配偶瘦小"

        return "配偶容貌身材中等"

    def _analyze_marriage_timing(self):
        """十四、论夫妻看见大或小"""
        result = []

        # 检查天干或地支有两个相同的字
        all_stems = [p['stem'] for p in self.bazi_pillars.values()]
        all_branches = [p['branch'] for p in self.bazi_pillars.values()]

        stem_counts = {stem: all_stems.count(stem) for stem in set(all_stems)}
        branch_counts = {branch: all_branches.count(branch) for branch in set(all_branches)}

        if any(count >= 2 for count in stem_counts.values()) or any(count >= 2 for count in branch_counts.values()):
            result.append("天干或地支有重复字，晚婚或晚育")

        # 日支或月支是子午卯酉，容易有外遇
        day_branch = self.day_branch
        month_branch = self.bazi_pillars['month']['branch']

        if day_branch in ['子', '午', '卯', '酉'] or month_branch in ['子', '午', '卯', '酉']:
            result.append("日支或月支在子午卯酉中，容易有外遇")

        return "；".join(result) if result else "婚恋时间相对正常"

    def _analyze_children(self):
        """十五、子女情况"""
        stems = [
            self.bazi_pillars['year']['stem'],
            self.bazi_pillars['month']['stem'],
            self.bazi_pillars['day']['stem'],
            self.bazi_pillars['hour']['stem']
        ]

        # 天干见戊或己其中之一，子女小富贵
        has_wu = '戊' in stems
        has_ji = '己' in stems

        if has_wu and has_ji:
            return "天干见戊己二字，子女大富贵"
        elif has_wu or has_ji:
            return "天干见戊或己，子女小富贵"
        else:
            return "子女运势普通"

    def _analyze_children_harm(self):
        """十六、克害子女"""
        day_pillar = f"{self.day_stem}{self.day_branch}"

        if day_pillar in BAD_CHILDREN_PILLARS:
            return f"日柱{day_pillar}在{BAD_CHILDREN_PILLARS}中，不利子女"

        return "无明显克害子女特征"

    def _analyze_glasses(self):
        """十七、带眼镜之人"""
        stems = [
            self.bazi_pillars['year']['stem'],
            self.bazi_pillars['month']['stem'],
            self.bazi_pillars['day']['stem'],
            self.bazi_pillars['hour']['stem']
        ]

        branches = [
            self.bazi_pillars['year']['branch'],
            self.bazi_pillars['month']['branch'],
            self.bazi_pillars['day']['branch'],
            self.bazi_pillars['hour']['branch']
        ]

        result = []

        # 1、日干见丙之人
        if self.day_stem == '丙':
            result.append("日干为丙，易戴眼镜")

        # 2、年干、月干、日干、时干见丙庚或丁癸或丙丁或壬丙二字之人
        for pair in GLASSES_STEM_PAIRS:
            if pair[0] in stems and pair[1] in stems:
                result.append(f"天干见{pair[0]}{pair[1]}，易戴眼镜")
                break

        # 3、年干、月干、日干、时干见壬癸丙丁其中一字，且地支见申字之人
        if any(stem in ['壬', '癸', '丙', '丁'] for stem in stems) and '申' in branches:
            result.append("天干见壬癸丙丁且地支见申，易戴眼镜")

        return "；".join(result) if result else "无明显戴眼镜特征"

    def _analyze_away_home(self):
        """十八、他乡谋生立业"""
        # 1、日干见壬者，他乡立业谋生
        if self.day_stem == '壬':
            return "日干为壬，他乡立业谋生"

        # 2、年支六冲月支者，他乡立业谋生
        year_branch = self.bazi_pillars['year']['branch']
        month_branch = self.bazi_pillars['month']['branch']

        if SIX_CONFLICTS.get(year_branch) == month_branch:
            return f"年支{year_branch}冲月支{month_branch}，他乡立业谋生"

        # 3、八字中五行水多之人，他乡立业谋生
        all_elements = []
        for pillar in self.bazi_pillars.values():
            all_elements.append(STEM_ELEMENTS[pillar['stem']])
            all_elements.append(BRANCH_ELEMENTS[pillar['branch']])

        water_count = all_elements.count('水')
        if water_count >= 3:  # 假设水多定义为至少3个水
            return f"八字中水元素有{water_count}个，水多，他乡立业谋生"

        return "无明显他乡谋生特征"

    def _analyze_house_direction(self):
        """十九、命主阳宅"""
        day_branch = self.day_branch

        direction = BRANCH_DIRECTIONS.get(day_branch, '未知')
        return f"日支{day_branch}代表{direction}方，阳宅大门可能朝向{direction}"

    def _analyze_lifespan(self):
        """二十、寿命"""
        day_branch = self.day_branch

        # 日支见酉亥其中一字，容易短寿
        if day_branch in ['酉', '亥']:
            return f"日支{day_branch}在酉亥中，可能短寿"

        return "寿命情况正常"

    def _analyze_near_miss(self):
        """二十一、有惊无险之人"""
        result = []

        branches_by_pillar = {
            '年支': self.bazi_pillars['year']['branch'],
            '月支': self.bazi_pillars['month']['branch'],
            '日支': self.day_branch,
            '时支': self.bazi_pillars['hour']['branch']
        }

        for pillar_name, branch in branches_by_pillar.items():
            if branch in NEAR_MISS_BRANCHES:
                if pillar_name == '年支':
                    result.append(f"{pillar_name}{branch}在辰戌酉亥中，10岁前或50岁后有惊无险")
                elif pillar_name == '月支':
                    result.append(f"{pillar_name}{branch}在辰戌酉亥中，20岁前或60岁后有惊无险")
                elif pillar_name == '日支':
                    result.append(f"{pillar_name}{branch}在辰戌酉亥中，30岁前或70岁后有惊无险")
                elif pillar_name == '时支':
                    result.append(f"{pillar_name}{branch}在辰戌酉亥中，40岁前或80岁后有惊无险")

        return "；".join(result) if result else "无明显有惊无险特征"

    def _analyze_illness(self):
        """二十二、病痛"""
        result = []

        # 1、天干见相同字会有慢性病
        all_stems = [p['stem'] for p in self.bazi_pillars.values()]
        stem_counts = {stem: all_stems.count(stem) for stem in set(all_stems)}
        if any(count >= 2 for count in stem_counts.values()):
            result.append("天干有重复字，可能有慢性病")

        # 2、日支是辰戌酉亥其中之一者易得慢性病
        if self.day_branch in ['辰', '戌', '酉', '亥']:
            result.append(f"日支{self.day_branch}在辰戌酉亥中，易得慢性病")

        # 3、日支是卯酉丑其中之一者，女人容易得妇科病
        if self.gender == 'female' and self.day_branch in ['卯', '酉', '丑']:
            result.append(f"女命日支{self.day_branch}在卯酉丑中，易得妇科病")

        return "；".join(result) if result else "无明显特殊病痛特征"