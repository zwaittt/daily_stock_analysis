# -*- coding: utf-8 -*-
"""
===================================
智能选股推荐模块
===================================

职责：
1. 追踪市场热点主线（板块分析）
2. 发现各板块龙头股
3. 分析资金流向
4. 综合评分推荐潜力股

使用 planning-with-files skill 开发
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

import akshare as ak
import pandas as pd

logger = logging.getLogger(__name__)


# ==================== 数据类 ====================

@dataclass
class SectorHotline:
    """板块热点数据"""
    name: str                    # 板块名称
    code: str                    # 板块代码
    change_pct: float = 0.0      # 涨跌幅
    turnover_rate: float = 0.0   # 换手率
    up_count: int = 0            # 上涨家数
    down_count: int = 0          # 下跌家数
    leader_stock: str = ""       # 领涨股
    leader_change_pct: float = 0.0  # 领涨股涨幅
    money_flow: float = 0.0      # 资金净流入（亿）
    sector_type: str = "industry"  # industry 或 concept
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'code': self.code,
            'change_pct': self.change_pct,
            'turnover_rate': self.turnover_rate,
            'up_count': self.up_count,
            'down_count': self.down_count,
            'leader_stock': self.leader_stock,
            'leader_change_pct': self.leader_change_pct,
            'money_flow': self.money_flow,
            'sector_type': self.sector_type,
        }


@dataclass
class StockRecommendation:
    """股票推荐数据"""
    code: str                    # 股票代码
    name: str                    # 股票名称
    price: float = 0.0           # 当前价格
    change_pct: float = 0.0      # 涨跌幅
    sector: str = ""             # 所属板块
    
    # 评分维度
    sector_score: float = 0.0    # 板块强度分 (0-30)
    leader_score: float = 0.0    # 龙头地位分 (0-25)
    money_score: float = 0.0     # 资金流入分 (0-25)
    tech_score: float = 0.0      # 技术形态分 (0-20)
    total_score: float = 0.0     # 综合评分 (0-100)
    
    # 详情
    is_limit_up: bool = False    # 是否涨停
    limit_up_days: int = 0       # 连板天数
    is_leader: bool = False      # 是否板块领涨
    money_flow_rank: int = 0     # 资金流入排名
    money_flow: float = 0.0      # 主力净流入（亿）
    is_new_high: bool = False    # 是否60日新高
    reason: str = ""             # 推荐理由
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'code': self.code,
            'name': self.name,
            'price': self.price,
            'change_pct': self.change_pct,
            'sector': self.sector,
            'total_score': self.total_score,
            'is_limit_up': self.is_limit_up,
            'limit_up_days': self.limit_up_days,
            'money_flow': self.money_flow,
            'is_new_high': self.is_new_high,
            'reason': self.reason,
        }


# ==================== 热点主线追踪 ====================

class HotLineTracker:
    """热点主线追踪器"""
    
    def __init__(self, sleep_min: float = 2.0, sleep_max: float = 4.0):
        self.sleep_min = sleep_min
        self.sleep_max = sleep_max
    
    def _random_sleep(self):
        """随机休眠防止被封"""
        import random
        sleep_time = random.uniform(self.sleep_min, self.sleep_max)
        time.sleep(sleep_time)
    
    def get_industry_hotlines(self, top_n: int = 10) -> List[SectorHotline]:
        """
        获取行业板块热点
        
        Returns:
            涨幅前N的行业板块列表
        """
        try:
            logger.info("[选股] 获取行业板块热点...")
            self._random_sleep()
            
            df = ak.stock_board_industry_name_em()
            
            if df is None or df.empty:
                logger.warning("[选股] 行业板块数据为空")
                return []
            
            hotlines = []
            for _, row in df.head(top_n).iterrows():
                hotline = SectorHotline(
                    name=str(row.get('板块名称', '')),
                    code=str(row.get('板块代码', '')),
                    change_pct=float(row.get('涨跌幅', 0) or 0),
                    turnover_rate=float(row.get('换手率', 0) or 0),
                    up_count=int(row.get('上涨家数', 0) or 0),
                    down_count=int(row.get('下跌家数', 0) or 0),
                    leader_stock=str(row.get('领涨股票', '')),
                    leader_change_pct=float(row.get('领涨股票-涨跌幅', 0) or 0),
                    sector_type='industry',
                )
                hotlines.append(hotline)
            
            logger.info(f"[选股] 获取到 {len(hotlines)} 个热点行业板块")
            return hotlines
            
        except Exception as e:
            logger.error(f"[选股] 获取行业板块热点失败: {e}")
            return []
    
    def get_concept_hotlines(self, top_n: int = 10) -> List[SectorHotline]:
        """
        获取概念板块热点
        
        Returns:
            涨幅前N的概念板块列表
        """
        try:
            logger.info("[选股] 获取概念板块热点...")
            self._random_sleep()
            
            df = ak.stock_board_concept_name_em()
            
            if df is None or df.empty:
                logger.warning("[选股] 概念板块数据为空")
                return []
            
            hotlines = []
            for _, row in df.head(top_n).iterrows():
                hotline = SectorHotline(
                    name=str(row.get('板块名称', '')),
                    code=str(row.get('板块代码', '')),
                    change_pct=float(row.get('涨跌幅', 0) or 0),
                    turnover_rate=float(row.get('换手率', 0) or 0),
                    up_count=int(row.get('上涨家数', 0) or 0),
                    down_count=int(row.get('下跌家数', 0) or 0),
                    leader_stock=str(row.get('领涨股票', '')),
                    leader_change_pct=float(row.get('领涨股票-涨跌幅', 0) or 0),
                    sector_type='concept',
                )
                hotlines.append(hotline)
            
            logger.info(f"[选股] 获取到 {len(hotlines)} 个热点概念板块")
            return hotlines
            
        except Exception as e:
            logger.error(f"[选股] 获取概念板块热点失败: {e}")
            return []
    
    def identify_main_lines(self, top_n: int = 5) -> List[SectorHotline]:
        """
        识别当前市场主线
        
        综合行业和概念板块，筛选出最强势的主线方向
        
        Returns:
            市场主线列表
        """
        # 获取行业和概念热点
        industry_hotlines = self.get_industry_hotlines(top_n=10)
        concept_hotlines = self.get_concept_hotlines(top_n=10)
        
        # 合并并按涨幅排序
        all_hotlines = industry_hotlines + concept_hotlines
        all_hotlines.sort(key=lambda x: x.change_pct, reverse=True)
        
        # 返回前N个作为主线
        main_lines = all_hotlines[:top_n]
        
        logger.info(f"[选股] 识别出 {len(main_lines)} 条市场主线")
        for ml in main_lines:
            logger.info(f"  - {ml.name}: {ml.change_pct:+.2f}% | 领涨: {ml.leader_stock}")
        
        return main_lines


# ==================== 龙头股发现 ====================

class LeaderFinder:
    """板块龙头发现器"""
    
    def __init__(self, sleep_min: float = 2.0, sleep_max: float = 4.0):
        self.sleep_min = sleep_min
        self.sleep_max = sleep_max
    
    def _random_sleep(self):
        import random
        time.sleep(random.uniform(self.sleep_min, self.sleep_max))
    
    def get_sector_leaders(self, sector_name: str, sector_type: str = "industry", top_n: int = 5) -> List[Dict]:
        """
        获取板块领涨股
        
        Args:
            sector_name: 板块名称
            sector_type: "industry" 或 "concept"
            top_n: 返回前N只
            
        Returns:
            领涨股列表
        """
        try:
            logger.info(f"[选股] 获取 {sector_name} 板块领涨股...")
            self._random_sleep()
            
            if sector_type == "industry":
                df = ak.stock_board_industry_cons_em(symbol=sector_name)
            else:
                df = ak.stock_board_concept_cons_em(symbol=sector_name)
            
            if df is None or df.empty:
                return []
            
            # 按涨跌幅排序
            df['涨跌幅'] = pd.to_numeric(df['涨跌幅'], errors='coerce')
            df = df.dropna(subset=['涨跌幅'])
            df = df.sort_values('涨跌幅', ascending=False)
            
            leaders = []
            for _, row in df.head(top_n).iterrows():
                leaders.append({
                    'code': str(row.get('代码', '')),
                    'name': str(row.get('名称', '')),
                    'price': float(row.get('最新价', 0) or 0),
                    'change_pct': float(row.get('涨跌幅', 0) or 0),
                    'turnover_rate': float(row.get('换手率', 0) or 0),
                    'sector': sector_name,
                })
            
            return leaders
            
        except Exception as e:
            logger.error(f"[选股] 获取 {sector_name} 领涨股失败: {e}")
            return []
    
    def get_limit_up_stocks(self, date: Optional[str] = None) -> List[Dict]:
        """
        获取涨停股池
        
        Args:
            date: 日期，格式 YYYYMMDD，默认今天
            
        Returns:
            涨停股列表（含连板信息）
        """
        try:
            if date is None:
                date = datetime.now().strftime('%Y%m%d')
            
            logger.info(f"[选股] 获取涨停股池 ({date})...")
            self._random_sleep()
            
            df = ak.stock_zt_pool_em(date=date)
            
            if df is None or df.empty:
                logger.warning("[选股] 涨停股池为空，尝试前一交易日")
                return []
            
            limit_ups = []
            for _, row in df.iterrows():
                limit_ups.append({
                    'code': str(row.get('代码', '')),
                    'name': str(row.get('名称', '')),
                    'price': float(row.get('最新价', 0) or 0),
                    'change_pct': float(row.get('涨跌幅', 0) or 0),
                    'limit_up_days': int(row.get('连板数', 1) or 1),
                    'seal_money': float(row.get('封板资金', 0) or 0),
                    'sector': str(row.get('所属行业', '')),
                    'first_time': str(row.get('首次封板时间', '')),
                    'break_count': int(row.get('炸板次数', 0) or 0),
                })
            
            logger.info(f"[选股] 获取到 {len(limit_ups)} 只涨停股")
            return limit_ups
            
        except Exception as e:
            logger.error(f"[选股] 获取涨停股池失败: {e}")
            return []
    
    def get_strong_stocks(self, date: Optional[str] = None, top_n: int = 50) -> List[Dict]:
        """
        获取强势股池（60日新高等）
        
        Returns:
            强势股列表
        """
        try:
            if date is None:
                date = datetime.now().strftime('%Y%m%d')
            
            logger.info(f"[选股] 获取强势股池 ({date})...")
            self._random_sleep()
            
            df = ak.stock_zt_pool_strong_em(date=date)
            
            if df is None or df.empty:
                return []
            
            strong_stocks = []
            for _, row in df.head(top_n).iterrows():
                strong_stocks.append({
                    'code': str(row.get('代码', '')),
                    'name': str(row.get('名称', '')),
                    'price': float(row.get('最新价', 0) or 0),
                    'change_pct': float(row.get('涨跌幅', 0) or 0),
                    'is_new_high': str(row.get('是否新高', '')) == '是',
                    'volume_ratio': float(row.get('量比', 0) or 0),
                    'reason': str(row.get('入选理由', '')),
                    'sector': str(row.get('所属行业', '')),
                })
            
            logger.info(f"[选股] 获取到 {len(strong_stocks)} 只强势股")
            return strong_stocks
            
        except Exception as e:
            logger.error(f"[选股] 获取强势股池失败: {e}")
            return []


# ==================== 资金流向分析 ====================

class MoneyFlowAnalyzer:
    """资金流向分析器"""
    
    def __init__(self, sleep_min: float = 2.0, sleep_max: float = 4.0):
        self.sleep_min = sleep_min
        self.sleep_max = sleep_max
    
    def _random_sleep(self):
        import random
        time.sleep(random.uniform(self.sleep_min, self.sleep_max))
    
    def get_sector_money_flow(self, sector_type: str = "行业资金流", top_n: int = 20) -> List[Dict]:
        """
        获取板块资金流向排名
        
        Args:
            sector_type: "行业资金流" 或 "概念资金流"
            top_n: 返回前N个板块
            
        Returns:
            板块资金流向列表
        """
        try:
            logger.info(f"[选股] 获取{sector_type}排名...")
            self._random_sleep()
            
            df = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type=sector_type)
            
            if df is None or df.empty:
                return []
            
            flows = []
            for _, row in df.head(top_n).iterrows():
                flows.append({
                    'name': str(row.get('名称', '')),
                    'change_pct': float(row.get('今日涨跌幅', 0) or 0),
                    'main_flow': float(row.get('今日主力净流入-净额', 0) or 0) / 1e8,  # 转亿
                    'main_flow_pct': float(row.get('今日主力净流入-净占比', 0) or 0),
                    'super_flow': float(row.get('今日超大单净流入-净额', 0) or 0) / 1e8,
                    'leader_stock': str(row.get('今日主力净流入最大股', '')),
                })
            
            logger.info(f"[选股] 获取到 {len(flows)} 个板块资金流向")
            return flows
            
        except Exception as e:
            logger.error(f"[选股] 获取板块资金流向失败: {e}")
            return []
    
    def get_stock_money_flow_rank(self, top_n: int = 50) -> List[Dict]:
        """
        获取个股资金净流入排名
        
        Returns:
            个股资金流入排名列表
        """
        try:
            logger.info("[选股] 获取个股资金流入排名...")
            self._random_sleep()
            
            df = ak.stock_individual_fund_flow_rank(indicator="今日")
            
            if df is None or df.empty:
                return []
            
            flows = []
            for i, (_, row) in enumerate(df.head(top_n).iterrows(), 1):
                flows.append({
                    'rank': i,
                    'code': str(row.get('代码', '')),
                    'name': str(row.get('名称', '')),
                    'price': float(row.get('最新价', 0) or 0),
                    'change_pct': float(row.get('涨跌幅', 0) or 0),
                    'main_flow': float(row.get('主力净流入-净额', 0) or 0) / 1e8,
                    'main_flow_pct': float(row.get('主力净流入-净占比', 0) or 0),
                })
            
            logger.info(f"[选股] 获取到 {len(flows)} 只个股资金流向")
            return flows
            
        except Exception as e:
            logger.error(f"[选股] 获取个股资金流向失败: {e}")
            return []


# ==================== 智能选股推荐 ====================

class StockRecommender:
    """
    智能选股推荐器
    
    整合热点追踪、龙头发现、资金分析，生成每日选股推荐
    """
    
    def __init__(self, analyzer=None):
        """
        初始化
        
        Args:
            analyzer: AI分析器实例（可选，用于生成AI点评）
        """
        self.hotline_tracker = HotLineTracker()
        self.leader_finder = LeaderFinder()
        self.money_flow_analyzer = MoneyFlowAnalyzer()
        self.analyzer = analyzer
        
        # 缓存
        self._main_lines: List[SectorHotline] = []
        self._limit_up_stocks: List[Dict] = []
        self._strong_stocks: List[Dict] = []
        self._money_flow_rank: List[Dict] = []
        self._sector_money_flow: List[Dict] = []
    
    def _collect_data(self):
        """收集所有需要的数据"""
        logger.info("========== 开始收集选股数据 ==========")
        
        # 1. 市场主线
        self._main_lines = self.hotline_tracker.identify_main_lines(top_n=5)
        
        # 2. 涨停股
        self._limit_up_stocks = self.leader_finder.get_limit_up_stocks()
        
        # 3. 强势股
        self._strong_stocks = self.leader_finder.get_strong_stocks(top_n=100)
        
        # 4. 个股资金流向
        self._money_flow_rank = self.money_flow_analyzer.get_stock_money_flow_rank(top_n=100)
        
        # 5. 板块资金流向
        self._sector_money_flow = self.money_flow_analyzer.get_sector_money_flow(top_n=30)
        
        logger.info("========== 数据收集完成 ==========")
    
    def _score_stock(self, code: str, name: str, base_info: Dict) -> StockRecommendation:
        """
        为单只股票评分
        
        评分维度：
        - 板块强度 (30分): 所属板块涨幅排名
        - 龙头地位 (25分): 是否板块领涨、连板数
        - 资金流入 (25分): 主力净流入排名
        - 技术形态 (20分): 60日新高、量比
        """
        rec = StockRecommendation(
            code=code,
            name=name,
            price=base_info.get('price', 0),
            change_pct=base_info.get('change_pct', 0),
            sector=base_info.get('sector', ''),
        )
        
        # 1. 板块强度分 (0-30)
        sector = base_info.get('sector', '')
        for i, ml in enumerate(self._main_lines):
            if sector and sector in ml.name:
                rec.sector_score = 30 - i * 5  # 第1主线30分，第2主线25分...
                rec.sector = ml.name
                break
        
        # 2. 龙头地位分 (0-25)
        # 检查是否涨停
        for zt in self._limit_up_stocks:
            if zt['code'] == code:
                rec.is_limit_up = True
                rec.limit_up_days = zt.get('limit_up_days', 1)
                rec.leader_score += 10 + min(rec.limit_up_days * 3, 15)  # 涨停10分 + 连板加分
                break
        
        # 检查是否板块领涨
        for ml in self._main_lines:
            if ml.leader_stock == name:
                rec.is_leader = True
                rec.leader_score += 10
                break
        
        rec.leader_score = min(rec.leader_score, 25)
        
        # 3. 资金流入分 (0-25)
        for flow in self._money_flow_rank:
            if flow['code'] == code:
                rec.money_flow_rank = flow['rank']
                rec.money_flow = flow['main_flow']
                # 排名越靠前分数越高
                if flow['rank'] <= 10:
                    rec.money_score = 25
                elif flow['rank'] <= 30:
                    rec.money_score = 20
                elif flow['rank'] <= 50:
                    rec.money_score = 15
                elif flow['rank'] <= 100:
                    rec.money_score = 10
                break
        
        # 4. 技术形态分 (0-20)
        for strong in self._strong_stocks:
            if strong['code'] == code:
                rec.is_new_high = strong.get('is_new_high', False)
                if rec.is_new_high:
                    rec.tech_score += 15
                volume_ratio = strong.get('volume_ratio', 0)
                if volume_ratio > 2:
                    rec.tech_score += 5
                break
        
        rec.tech_score = min(rec.tech_score, 20)
        
        # 计算总分
        rec.total_score = rec.sector_score + rec.leader_score + rec.money_score + rec.tech_score
        
        # 生成推荐理由
        reasons = []
        if rec.sector_score > 20:
            reasons.append(f"主线板块({rec.sector})")
        if rec.is_limit_up:
            if rec.limit_up_days > 1:
                reasons.append(f"连板{rec.limit_up_days}天")
            else:
                reasons.append("今日涨停")
        if rec.is_leader:
            reasons.append("板块领涨")
        if rec.money_flow > 5:
            reasons.append(f"资金抢筹({rec.money_flow:.1f}亿)")
        if rec.is_new_high:
            reasons.append("60日新高")
        
        rec.reason = " + ".join(reasons) if reasons else "综合表现良好"
        
        return rec
    
    def generate_recommendations(self, max_stocks: int = 10) -> List[StockRecommendation]:
        """
        生成今日选股推荐
        
        Args:
            max_stocks: 最多推荐股票数量
            
        Returns:
            推荐股票列表（按评分排序）
        """
        # 收集数据
        self._collect_data()
        
        # 构建候选池
        candidates: Dict[str, Dict] = {}
        
        # 从涨停股池中添加候选
        for stock in self._limit_up_stocks:
            code = stock['code']
            if code not in candidates:
                candidates[code] = stock
        
        # 从强势股池中添加候选
        for stock in self._strong_stocks:
            code = stock['code']
            if code not in candidates:
                candidates[code] = stock
        
        # 从资金流入排名中添加候选
        for stock in self._money_flow_rank[:50]:
            code = stock['code']
            if code not in candidates:
                candidates[code] = stock
        
        # 从主线板块领涨股添加候选
        for ml in self._main_lines[:3]:
            if ml.leader_stock:
                # 需要获取领涨股的详细信息
                leaders = self.leader_finder.get_sector_leaders(
                    ml.name, ml.sector_type, top_n=3
                )
                for leader in leaders:
                    code = leader['code']
                    if code not in candidates:
                        candidates[code] = leader
        
        logger.info(f"[选股] 候选池共 {len(candidates)} 只股票")
        
        # 评分
        recommendations = []
        for code, info in candidates.items():
            rec = self._score_stock(code, info.get('name', ''), info)
            if rec.total_score >= 30:  # 只保留30分以上的
                recommendations.append(rec)
        
        # 排序
        recommendations.sort(key=lambda x: x.total_score, reverse=True)
        
        # 取前N只
        top_recommendations = recommendations[:max_stocks]
        
        logger.info(f"[选股] 筛选出 {len(top_recommendations)} 只推荐股票")
        for rec in top_recommendations:
            logger.info(f"  - {rec.name}({rec.code}): {rec.total_score:.0f}分 | {rec.reason}")
        
        return top_recommendations
    
    def generate_report(self, recommendations: Optional[List[StockRecommendation]] = None) -> str:
        """
        生成选股推荐报告
        
        Args:
            recommendations: 推荐列表，如果为空则自动生成
            
        Returns:
            格式化的报告文本
        """
        if recommendations is None:
            recommendations = self.generate_recommendations()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 构建报告
        lines = [
            f"## 🎯 {today} 智能选股推荐",
            "",
            "### 📊 今日市场主线",
            "━" * 20,
        ]
        
        # 主线板块
        for i, ml in enumerate(self._main_lines[:5], 1):
            emoji = "🔥" if ml.change_pct > 2 else "📈" if ml.change_pct > 0 else "📉"
            flow_info = ""
            for sf in self._sector_money_flow:
                if sf['name'] == ml.name:
                    flow_info = f" | 资金: {sf['main_flow']:+.1f}亿"
                    break
            lines.append(f"{emoji} **主线{i}**: {ml.name} ({ml.change_pct:+.2f}%){flow_info}")
            lines.append(f"   领涨: {ml.leader_stock} ({ml.leader_change_pct:+.2f}%)")
        
        lines.append("")
        lines.append("### 💎 今日潜力股推荐")
        lines.append("━" * 20)
        
        # 推荐股票
        star_map = {5: "⭐⭐⭐⭐⭐", 4: "⭐⭐⭐⭐", 3: "⭐⭐⭐", 2: "⭐⭐", 1: "⭐"}
        
        for i, rec in enumerate(recommendations, 1):
            # 根据分数计算星级
            if rec.total_score >= 70:
                stars = star_map[5]
            elif rec.total_score >= 55:
                stars = star_map[4]
            elif rec.total_score >= 40:
                stars = star_map[3]
            else:
                stars = star_map[2]
            
            lines.append(f"**{i}️⃣ {rec.name}({rec.code})** {stars}")
            
            # 标签
            tags = []
            if rec.is_limit_up:
                tags.append(f"🔴涨停" + (f"(连板{rec.limit_up_days})" if rec.limit_up_days > 1 else ""))
            if rec.is_leader:
                tags.append("👑领涨")
            if rec.is_new_high:
                tags.append("📈新高")
            if rec.sector:
                tags.append(f"📌{rec.sector}")
            
            if tags:
                lines.append(f"   {' '.join(tags)}")
            
            # 资金信息
            if rec.money_flow > 0:
                lines.append(f"   💰 主力净流入: {rec.money_flow:.2f}亿 (排名第{rec.money_flow_rank})")
            
            # 推荐理由
            lines.append(f"   📋 理由: {rec.reason}")
            lines.append("")
        
        # 风险提示
        lines.extend([
            "### ⚠️ 风险提示",
            "以上推荐仅供参考，不构成投资建议。",
            "股市有风险，投资需谨慎。",
            "",
            "━" * 20,
            f"*生成时间: {datetime.now().strftime('%H:%M')}*",
        ])
        
        return "\n".join(lines)
    
    def run_daily_recommendation(self) -> str:
        """
        执行每日选股推荐流程
        
        Returns:
            推荐报告文本
        """
        logger.info("========== 开始每日智能选股 ==========")
        
        try:
            # 生成推荐
            recommendations = self.generate_recommendations(max_stocks=10)
            
            # 生成报告
            report = self.generate_report(recommendations)
            
            logger.info("========== 智能选股完成 ==========")
            
            return report
            
        except Exception as e:
            logger.error(f"[选股] 执行失败: {e}")
            return f"⚠️ 智能选股执行失败: {e}"


# ==================== 测试入口 ====================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '.')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    )
    
    print("=" * 60)
    print("智能选股推荐测试")
    print("=" * 60)
    
    recommender = StockRecommender()
    report = recommender.run_daily_recommendation()
    
    print("\n" + "=" * 60)
    print("推荐报告:")
    print("=" * 60)
    print(report)
