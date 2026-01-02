"""
高级内容过滤器 - 多层次文本规范化 + 模糊匹配
用于检测和过滤敏感内容，防止简单的绕过技巧
"""

import re
from typing import Set, List, Tuple, Dict
from difflib import SequenceMatcher


class ContentFilter:
    """内容过滤器类"""
    
    # 内置默认屏蔽词库
    DEFAULT_KEYWORDS = {
        # NSFW / 色情
        'nsfw', 'porn', 'sex', 'hentai', 'ecchi', 'xxx', 'r18', 'adult', 'sexual', 'explicit',
        'nude', 'nudity', 'naked', 'unclothed', 'topless', 'bare', 'exposed',
        
        # 暴力 / 恐怖 (Violence / Horror)
        'violence', 'violent', 'kill', 'killing', 'murder', 'death', 'dead', 'suicide',
        'assault', 'attack', 'weapon', 'gun', 'knife', 'execution', 'torture', 'beating',
        'strangle', 'hanging', 'drowning', 'terrorist', 'war',
        
        # 血腥 / 恶心 (Blood / Gore / Disgusting)
        'blood', 'bloody', 'gore', 'gory', 'bloadshed', 'slaughter', 'butcher', 'carcass',
        'hemorrhage', 'mutilation', 'organ', 'intestine', 'eyeball', 'gut', 'splat',
        'fracture', 'bruise', 'scar', 'wound', 'vomit', 'feces', 'shitting',
        
        # 猎奇 / 变态 (Bizarre / Guro / Creepy)
        'guro', 'amputation', 'dismember', 'necrophilia', 'bestiality', '畸形', '变态',
        '肢解', '断肢', '尸体', '虐待', '内脏', '肠子', '剥皮', '碎尸', '腐烂', 'rotten',
        'decaying', 'zombie', 'scary', 'spooky', 'creepy',
        
        # 中文敏感词
        '色情', '裸露', '暴力', '血腥', '猎奇', '杀人', '自杀', '邪教', '毒品', '强奸', '黄片',
    }

    def __init__(self, blocked_keywords: Set[str] = None, use_defaults: bool = True):
        """
        初始化内容过滤器
        
        Args:
            blocked_keywords: 自定义的黑名单关键词集合
            use_defaults: 是否使用内置的默认屏蔽词
        """
        self.blocked_keywords = blocked_keywords or set()
        if use_defaults:
            self.blocked_keywords.update(self.DEFAULT_KEYWORDS)

        
        # 同义词词典 - 将常见的绕过词映射到标准词
        self.synonym_map = {
            # NSFW相关
            'n.s.f.w': 'nsfw', 'n s f w': 'nsfw', 'n-s-f-w': 'nsfw', 'not safe for work': 'nsfw',
            'r-18': 'r18', 'r 18': 'r18', 'adult content': 'adult', 'xxx': 'porn', '18+': 'r18', '18plus': 'r18',
            
            # 裸露相关
            'unclothed': 'nude', 'undressed': 'nude', 'bare': 'naked', 'topless': 'nude', 'exposed': 'nude',
            
            # 暴力相关 (Violence)
            'violent': 'violence', 'brutal': 'violence', 'killing': 'kill', 'murder': 'kill',
            'suicide': 'suicide', 'assault': 'violence', 'execution': 'violence', 'torture': 'violence',
            'beating': 'violence', 'strangulation': 'violence', 'hanging': 'violence',
            '武器': 'weapon', '枪支': 'weapon', '处决': 'violence', '殴打': 'violence',
            
            # 血腥相关 (Bloody/Gore)
            'gory': 'gore', 'bloody': 'blood', 'bloodshed': 'blood', 'slaughter': 'blood',
            'hemorrhage': 'blood', 'wound': 'blood', 'mutilation': 'blood', 'carcass': 'blood',
            '鲜血': 'blood', '流血': 'blood', '屠杀': 'blood', '伤口': 'blood',
            
            # 猎奇相关 (Bizarre/Guro)
            'guro': 'guro', 'amputation': 'guro', 'dismemberment': 'guro', 'necrophilia': 'guro',
            'bestiality': 'guro', 'intestines': 'guro', 'internal organs': 'guro', 'eyeball': 'guro',
            'mutilated': 'guro', 'bizarre': 'guro', 'disturbing': 'guro',
            '肢解': 'guro', '断肢': 'guro', '尸体': 'guro', '畸形': 'guro', '变态': 'guro',
            '内脏': 'guro', '肠子': 'guro', '碎尸': 'guro', '剥皮': 'guro',
            
            # 中文通用
            '色情': 'nsfw', '露骨': 'explicit', '裸露': 'nude', '成人': 'adult', '十八禁': 'r18',
        }
        
        # 拼音映射 - 常见中文敏感词的拼音及缩写
        self.pinyin_map = {
            # 暴力
            'baoli': '暴力', 'bl': '暴力', 'sharen': '杀人', 'sr': '杀人', 'zisha': '自杀', 'zs': '自杀',
            'wuqi': '武器', 'wq': '武器', 'qiang': '枪支', 'chujue': '处决',
            
            # 血腥
            'xue': '血', 'xueye': '血液', 'xy': '血液', 'xuexing': '血腥', 'xx': '血腥',
            'tusha': '屠杀', 'ts': '屠杀', 'shangkou': '伤口', 'sk': '伤口',
            
            # 猎奇
            'lieqi': '猎奇', 'lq': '猎奇', 'zhijie': '肢解', 'zj': '肢解', 'duanzhi': '断肢', 'dz': '断肢',
            'shiti': '尸体', 'st': '尸体', 'neizang': '内脏', 'nz': '内脏', 'changzi': '肠子', 'cz': '肠子',
            'biantai': '变态', 'bt': '变态', 'jixing': '畸形', 'jx': '畸形',
            
            # NSFW
            'seqing': '色情', 'sq': '色情', 'luoti': '裸体', 'lt': '裸体', 'huang': '黄',
        }
        
        # 正则模式 - 匹配字符间插入特殊符号逃避检测的情况
        self.pattern_rules = [
            # 匹配字符间插入空格、点、横线、下划线、星号等
            (r'n[\s\.\-_\*]*s[\s\.\-_\*]*f[\s\.\-_\*]*w', 'nsfw'),
            (r'r[\s\.\-_\*]*1[\s\.\-_\*]*8', 'r18'),
            (r'b[\s\.\-_\*]*l[\s\.\-_\*]*o[\s\.\-_\*]*o[\s\.\-_\*]*d', 'blood'),
            (r'g[\s\.\-_\*]*o[\s\.\-_\*]*r[\s\.\-_\*]*e', 'gore'),
            (r'n[\s\.\-_\*]*u[\s\.\-_\*]*d[\s\.\-_\*]*e', 'nude'),
            (r'p[\s\.\-_\*]*o[\s\.\-_\*]*r[\s\.\-_\*]*n', 'porn'),
            (r'v[\s\.\-_\*]*i[\s\.\-_\*]*o[\s\.\-_\*]*l[\s\.\-_\*]*e[\s\.\-_\*]*n[\s\.\-_\*]*c[\s\.\-_\*]*e', 'violence'),
            (r'g[\s\.\-_\*]*u[\s\.\-_\*]*r[\s\.\-_\*]*o', 'guro'),
            (r't[\s\.\-_\*]*o[\s\.\-_\*]*r[\s\.\-_\*]*t[\s\.\-_\*]*u[\s\.\-_\*]*r[\s\.\-_\*]*e', 'torture'),
            (r'k[\s\.\-_\*]*i[\s\.\-_\*]*l[\s\.\-_\*]*l', 'kill'),
            (r's[\s\.\-_\*]*e[\s\.\-_\*]*x', 'sex'),
        ]
    
    def normalize_text(self, text: str) -> str:
        """
        文本规范化：去除空格、标点、转小写
        
        Args:
            text: 原始文本
            
        Returns:
            规范化后的文本
        """
        # 转小写
        text = text.lower()
        # 移除常见的分隔符和标点
        text = re.sub(r'[\s\.\-_,，。、！!？?；;：:\'\"()（）\[\]【】{}｛｝<>《》]', '', text)
        return text
    
    def calculate_similarity(self, str1: str, str2: str) -> float:
        """
        计算两个字符串的相似度（使用序列匹配器）
        
        Args:
            str1: 字符串1
            str2: 字符串2
            
        Returns:
            相似度 (0.0-1.0)
        """
        return SequenceMatcher(None, str1, str2).ratio()
    
    def fuzzy_match(self, word: str, keyword: str, threshold: float = 0.85) -> bool:
        """
        模糊匹配 - 使用编辑距离判断相似度
        """
        # 规范化后再比较
        normalized_word = self.normalize_text(word)
        normalized_keyword = self.normalize_text(keyword)
        
        if not normalized_word or not normalized_keyword:
            return False

        # 检查单词是否包含敏感词 (如 word="pornography", keyword="porn")
        if normalized_keyword in normalized_word:
            return True
        
        # 计算相似度
        similarity = self.calculate_similarity(normalized_word, normalized_keyword)
        return similarity >= threshold
    
    def check_synonyms(self, text: str) -> List[str]:
        """
        检查文本中是否包含同义词
        """
        found = []
        normalized_text = self.normalize_text(text)
        words = [self.normalize_text(w) for w in re.split(r'[,，\s]+', text) if w.strip()]
        
        for synonym, standard in self.synonym_map.items():
            normalized_synonym = self.normalize_text(synonym)
            
            # 方法1: 精确单词匹配
            if any(normalized_synonym == w for w in words):
                found.append(f"{synonym} → {standard}")
                continue
                
            # 方法2: 全文本包含匹配 (仅针对较长的同义词短语，如 "not safe for work")
            if len(normalized_synonym) > 5 and normalized_synonym in normalized_text:
                found.append(f"{synonym} → {standard}")
        
        return found
    
    def check_pinyin(self, text: str) -> List[str]:
        """
        检查文本中是否包含拼音形式的敏感词
        """
        found = []
        words = [self.normalize_text(w) for w in re.split(r'[,，\s]+', text) if w.strip()]
        
        for pinyin, chinese in self.pinyin_map.items():
            normalized_pinyin = self.normalize_text(pinyin)
            for w in words:
                # 针对极短的拼音缩写（如 bl, st, bt），要求精确匹配或作为独立单词存在
                if len(normalized_pinyin) <= 2:
                    if normalized_pinyin == w:
                        found.append(f"{pinyin} → {chinese}")
                        break
                else:
                    # 较长的拼音可以允许包含匹配
                    if normalized_pinyin in w:
                        found.append(f"{pinyin} → {chinese}")
                        break
        
        return found
    
    def check_patterns(self, text: str) -> List[str]:
        """
        使用正则模式检查文本
        
        Args:
            text: 待检查的文本
            
        Returns:
            匹配的模式列表
        """
        found = []
        text_lower = text.lower()
        
        for pattern, keyword in self.pattern_rules:
            if re.search(pattern, text_lower):
                found.append(f"模式匹配: {keyword}")
        
        return found
    
    def check_keywords(self, text: str, fuzzy: bool = True) -> List[str]:
        """
        检查文本中是否包含黑名单关键词
        
        Args:
            text: 待检查的文本
            fuzzy: 是否启用模糊匹配
            
        Returns:
            发现的关键词列表
        """
        found = []
        words = re.split(r'[,，\s]+', text)
        
        for word in words:
            if not word.strip():
                continue
                
            for keyword in self.blocked_keywords:
                if fuzzy:
                    if self.fuzzy_match(word, keyword):
                        found.append(keyword)
                else:
                    if keyword.lower() in word.lower():
                        found.append(keyword)
        
        return list(set(found))  # 去重
    
    def check_content(self, text: str, enable_fuzzy: bool = True) -> Tuple[bool, Dict[str, List[str]]]:
        """
        综合检查文本内容
        
        Args:
            text: 待检查的文本
            enable_fuzzy: 是否启用模糊匹配
            
        Returns:
            (是否包含敏感内容, 检测详情)
        """
        details = {
            'keywords': [],      # 直接关键词匹配
            'synonyms': [],      # 同义词匹配
            'pinyin': [],        # 拼音匹配
            'patterns': [],      # 模式匹配
        }
        
        # 检查各种类型
        details['keywords'] = self.check_keywords(text, fuzzy=enable_fuzzy)
        details['synonyms'] = self.check_synonyms(text)
        details['pinyin'] = self.check_pinyin(text)
        details['patterns'] = self.check_patterns(text)
        
        # 判断是否包含敏感内容
        has_violation = any([
            len(details['keywords']) > 0,
            len(details['synonyms']) > 0,
            len(details['pinyin']) > 0,
            len(details['patterns']) > 0,
        ])
        
        return has_violation, details
    
    def get_violation_summary(self, details: Dict[str, List[str]]) -> str:
        """
        获取违规内容摘要
        
        Args:
            details: 检测详情
            
        Returns:
            违规摘要文本
        """
        messages = []
        
        if details['keywords']:
            messages.append(f"关键词: {', '.join(details['keywords'])}")
        if details['synonyms']:
            messages.append(f"同义词: {', '.join(details['synonyms'])}")
        if details['pinyin']:
            messages.append(f"拼音: {', '.join(details['pinyin'])}")
        if details['patterns']:
            messages.append(f"模式: {', '.join(details['patterns'])}")
        
        return ' | '.join(messages) if messages else '无违规'
