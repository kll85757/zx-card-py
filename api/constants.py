from typing import Dict, Any


def load_constants_from_readme() -> Dict[str, Any]:
    # MVP: hardcode minimal set; real impl could parse __NUXT__ dumps
    return {
        "color": ["无", "红", "蓝", "白", "黑", "绿"],
        "rarity": [["R", "R"], ["SR", "SR"], ["UR", "UR"], ["WR", "WR"], ["BR", "BR"], ["OBR", "OBR"]],
        "type": ["玩家", "玩家EX", "Z/X", "Z/X EX", "Z/X OB", "Z/X TOKEN", "事件", "事件EX", "升格", "升格EX", "剑临", "标记", "链结"],
        "mark": [["", "无"], ["ES", "觉醒之种"], ["IG", "点燃"]],
        "tags": ["生命恢复", "起始卡", "门扉卡", "超限驱动"],
        "series": {},
    }


