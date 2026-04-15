# INDICATORS.md

指标与检测条件开发指南 - 如何扩展新的技术指标和检测条件。

## 概述

系统采用插件化架构，新增指标或检测条件只需：
1. 实现相应的抽象基类
2. 注册到对应的 Registry
3. 无需修改核心代码

## 添加新指标

### Step 1: 创建指标实现类

在 `src/indicators/` 目录下创建新文件：

```python
# src/indicators/macd.py
from typing import Dict, Union
import pandas as pd
from src.indicators.base import Indicator

class MACDIndicator(Indicator):
    """MACD 指标"""
    
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self._fast = fast
        self._slow = slow
        self._signal = signal
    
    @property
    def name(self) -> str:
        return "MACD"
    
    @property
    def required_data(self) -> str:
        return "daily_kline"  # 数据类型
    
    @property
    def min_data_length(self) -> int:
        return self._slow + self._signal  # 至少需要 slow+signal 条数据
    
    @property
    def output_fields(self) -> list:
        return ["DIF", "DEA", "MACD"]  # 返回多个序列
    
    def calculate(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """计算 MACD"""
        close = data["close"]
        
        # EMA 计算
        ema_fast = close.ewm(span=self._fast, adjust=False).mean()
        ema_slow = close.ewm(span=self._slow, adjust=False).mean()
        
        # DIF = EMA(fast) - EMA(slow)
        dif = ema_fast - ema_slow
        
        # DEA = DIF 的 EMA(signal)
        dea = dif.ewm(span=self._signal, adjust=False).mean()
        
        # MACD = (DIF - DEA) * 2
        macd = (dif - dea) * 2
        
        return {
            "DIF": dif,
            "DEA": dea,
            "MACD": macd
        }
```

### Step 2: 注册指标

在初始化代码或配置中注册：

```python
from src.indicators.registry import get_registry
from src.indicators.macd import MACDIndicator

registry = get_registry()
registry.register(MACDIndicator(fast=12, slow=26, signal=9))
```

### Step 3: 更新配置

在 `config.py` 中添加配置：

```python
INDICATOR_CONFIGS = {
    "daily_kline": {
        "ma": {"short": 5, "long": 20},
        "macd": {"fast": 12, "slow": 26, "signal": 9},  # 新增
    }
}
```

## 添加新检测条件

### Step 1: 创建检测条件类

在 `src/detection/` 目录下创建新文件：

```python
# src/detection/macd_cross.py
from typing import Dict, List, Optional
import pandas as pd
from src.detection.base import Signal, SignalCondition

class MACDCrossCondition(SignalCondition):
    """MACD 金叉检测"""
    
    @property
    def name(self) -> str:
        return "macd_golden_cross"
    
    @property
    def required_indicators(self) -> List[str]:
        return ["DIF", "DEA"]  # 需要这两个指标
    
    @property
    def data_type(self) -> str:
        return "daily_kline"
    
    @property
    def description(self) -> str:
        return "MACD 金叉（DIF上穿DEA）"
    
    def detect(
        self,
        code: str,
        name: str,
        data: pd.DataFrame,
        indicators: Dict[str, pd.Series]
    ) -> Optional[Signal]:
        """检测 MACD 金叉"""
        dif = indicators.get("DIF")
        dea = indicators.get("DEA")
        
        if dif is None or dea is None:
            return None
        
        if len(dif) < 2 or len(dea) < 2:
            return None
        
        # 当前值和前一个值
        curr_dif = dif.iloc[-1]
        prev_dif = dif.iloc[-2]
        curr_dea = dea.iloc[-1]
        prev_dea = dea.iloc[-2]
        
        # 检查有效值
        if pd.isna(curr_dif) or pd.isna(curr_dea):
            return None
        
        # 金叉条件：前一根DIF<=DEA，当前DIF>DEA
        if prev_dif <= prev_dea and curr_dif > curr_dea:
            close = data["close"].iloc[-1]
            last_time = data["time"].iloc[-1]
            
            return Signal(
                code=code,
                name=name,
                condition=self.name,
                values={
                    "DIF": round(curr_dif, 2),
                    "DEA": round(curr_dea, 2),
                    "MACD": round((curr_dif - curr_dea) * 2, 2),
                    "close": round(close, 2)
                },
                data_time=str(last_time)[:10],
                message=f"{name}({code}) MACD金叉: DIF={curr_dif:.2f}, DEA={curr_dea:.2f}"
            )
        
        return None
```

### Step 2: 注册检测条件

```python
from src.detection.registry import get_signal_registry
from src.detection.macd_cross import MACDCrossCondition

signal_registry = get_signal_registry()
signal_registry.register(MACDCrossCondition())
```

### Step 3: 创建整合的检测器

```python
from src.indicators.engine import IndicatorEngine, create_default_engine_daily
from src.indicators.macd import MACDIndicator
from src.detection.detector import SignalDetector
from src.detection.registry import SignalRegistry
from src.detection.golden_cross import GoldenCrossCondition
from src.detection.macd_cross import MACDCrossCondition

# 创建指标引擎（注册所需指标）
indicator_registry = IndicatorRegistry()
indicator_registry.register(MAIndicator(5))
indicator_registry.register(MAIndicator(20))
indicator_registry.register(MACDIndicator())  # 新增

indicator_engine = IndicatorEngine(indicator_registry)

# 创建信号检测器（注册检测条件）
signal_registry = SignalRegistry()
signal_registry.register(GoldenCrossCondition())
signal_registry.register(MACDCrossCondition())  # 新增

detector = SignalDetector(signal_registry, indicator_engine)
```

## 完整示例：添加 KDJ 指标和超买超卖检测

### 1. KDJ 指标实现

```python
# src/indicators/kdj.py
from typing import Dict
import pandas as pd
from src.indicators.base import Indicator

class KDJIndicator(Indicator):
    """KDJ 指标"""
    
    def __init__(self, n: int = 9, m1: int = 3, m2: int = 3):
        self._n = n
        self._m1 = m1
        self._m2 = m2
    
    @property
    def name(self) -> str:
        return "KDJ"
    
    @property
    def required_data(self) -> str:
        return "daily_kline"
    
    @property
    def min_data_length(self) -> int:
        return self._n
    
    @property
    def output_fields(self) -> list:
        return ["K", "D", "J"]
    
    def calculate(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        close = data["close"]
        low = data["low"]
        high = data["high"]
        
        # RSV 计算
        low_n = low.rolling(window=self._n).min()
        high_n = high.rolling(window=self._n).max()
        rsv = (close - low_n) / (high_n - low_n) * 100
        
        # K, D, J 计算
        k = rsv.ewm(alpha=1/self._m1, adjust=False).mean()
        d = k.ewm(alpha=1/self._m2, adjust=False).mean()
        j = 3 * k - 2 * d
        
        return {"K": k, "D": d, "J": j}
```

### 2. KDJ 超买检测条件

```python
# src/detection/kdj_overbought.py
from typing import Dict, List, Optional
import pandas as pd
from src.detection.base import Signal, SignalCondition

class KDJOverboughtCondition(SignalCondition):
    """KDJ 超买检测（J > 100）"""
    
    @property
    def name(self) -> str:
        return "kdj_overbought"
    
    @property
    def required_indicators(self) -> List[str]:
        return ["K", "D", "J"]
    
    @property
    def description(self) -> str:
        return "KDJ 超买（J值 > 100）"
    
    def detect(self, code, name, data, indicators) -> Optional[Signal]:
        j = indicators.get("J")
        
        if j is None or len(j) < 1:
            return None
        
        curr_j = j.iloc[-1]
        
        if pd.isna(curr_j):
            return None
        
        # 超买条件：J > 100
        if curr_j > 100:
            k = indicators["K"].iloc[-1]
            d = indicators["D"].iloc[-1]
            
            return Signal(
                code=code,
                name=name,
                condition=self.name,
                values={"K": round(k, 2), "D": round(d, 2), "J": round(curr_j, 2)},
                data_time=str(data["time"].iloc[-1])[:10],
                message=f"{name}({code}) KDJ超买: J={curr_j:.2f}"
            )
        
        return None
```

## 最佳实践

### 1. 指标命名
- 使用大写字母和数字，如 `MA5`, `MACD`, `KDJ`
- 多值指标的输出字段要明确，如 `DIF`, `DEA`, `MACD`

### 2. 数据验证
- 在 `calculate()` 中处理边界情况
- 使用 `safe_calculate()` 者手动验证

### 3. 检测条件
- 明确 `required_indicators`，确保指标已注册
- 在 `detect()` 中检查数据有效性

### 4. Signal 构建
- 填充完整的 `values` 和 `message`
- `data_time` 格式为 `YYYY-MM-DD`

### 5. 测试
- 为新指标和检测条件编写单元测试
- 测试边界情况（数据不足、NaN值等）