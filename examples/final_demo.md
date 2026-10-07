# ClothingMatching-CN Skill 离线演示

本演示只使用仓库中的 JSON 样例和本地 Python 模块，不使用 API key、网络请求或图片生成。

## 1. 输入

- 用户档案：`examples/user_profile.json`
- 衣橱：`examples/wardrobe.json`
- 请求：`examples/sample_request.json`

请求为 `client_meeting`，目标是得体且亲和，并指定：

```json
{
  "must_use_item_ids": ["outerwear_black_oversized_blazer"],
  "avoid_item_ids": [],
  "requested_outfit_count": 3
}
```

## 2. 执行

```bash
python examples/run_demo.py
```

该脚本调用现有公共接口 `generate_outfits()`，流程为：

```text
User Profile → Wardrobe Data → Constraint Validation
→ Candidate Outfit Combinations → Compatibility Analysis
→ Ranking → Final Recommendations
```

## 3. 当前代码的实际结果

```text
outfit_count=2
rank=1 score=0.9633 major_item_ids={
  'outerwear': 'outerwear_black_oversized_blazer',
  'top': 'top_ivory_knit_shell',
  'bottom': 'bottom_charcoal_wide_leg_trousers',
  'shoes': 'shoes_black_leather_loafers',
  'bag': 'bag_black_structured_shoulder'
}
rank=2 score=0.9500 major_item_ids={
  'outerwear': 'outerwear_black_oversized_blazer',
  'dress_or_one_piece': 'dress_navy_knit_midi',
  'shoes': 'shoes_black_leather_loafers',
  'bag': 'bag_black_structured_shoulder'
}
warning=Only 2 valid unique major-item combinations are available; 3 were requested.
```

两套方案分别是「上衣＋下装」和「连衣裙」模板。黑色宽松西装外套位于 `outerwear` 槽位并标记为 `must_use`。主搭配依据真实 major-item IDs 去重，因此不会为了凑满请求数量而复制或仅改写风格名称。

第一套因场合、用户风格偏好、颜色偏好、衣橱覆盖和实际单品标签的组合信号得到 `0.9633`；第二套按自身实际内容独立计算，得到 `0.9500`。这些分数仅用于排序，不是服装质量或审美的客观评价。

## 4. 已知限制

- 分析依赖样例中已知的衣物、尺寸和元数据；未知数据不会被补造。
- 结果不保证真实合身、天气适配或多物同时装入包袋。
- 本项目当前不执行实时购物搜索，也不生成实际图片。
