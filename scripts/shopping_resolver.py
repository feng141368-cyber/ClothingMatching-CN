"""Provider-agnostic mock shopping resolution for established wardrobe gaps."""
from __future__ import annotations
import json
from urllib.parse import urlparse
from pathlib import Path
from typing import Any, Protocol

CATALOG = Path(__file__).resolve().parents[1] / "data" / "sample_products.json"
WEIGHTS = {"attribute_match": .30, "style_match": .15, "occasion_match": .15, "budget_match": .15, "size_availability": .10, "wardrobe_compatibility": .10, "feature_match": .05}

class ProductProvider(Protocol):
 def search(self, shopping_spec: dict[str, Any]) -> list[dict[str, Any]]: ...

class MockProductProvider:
 def __init__(self, products: list[dict[str, Any]] | None = None):
  self.products = products or json.loads(CATALOG.read_text(encoding="utf-8"))
 def search(self, shopping_spec): return [p for p in self.products if p["category"] == shopping_spec["required"].get("category")]

def build_shopping_spec(missing_item, user_profile=None, outfit_context=None, constraints=None):
 p=user_profile or {}; c=constraints or {}; m=missing_item or {}
 return {"required":{"category":m.get("category"),"sub_category":m.get("sub_category")},
 "preferred":{"colors":[m["color"]] if m.get("color") else [],"silhouettes":[m.get("silhouette")] if m.get("silhouette") else [],"materials":[],"structure":[m["structure"]] if m.get("structure") else []},
 "style_modes":p.get("style_modes",[]),"occasion":(outfit_context or {}).get("occasion",[]),"required_features":[], "preferred_features":[], "size_constraints":c.get("size_constraints",{}),
 "budget":{"currency":p.get("budget",{}).get("currency"),"max_price":p.get("budget",{}).get("max_total")},
 "brand_preferences":c.get("brand_preferences",{"preferred":[],"avoid":[]}),"shopping_region":c.get("shopping_region"),"source_policy":{"official_sources_only":c.get("official_sources_only",True)}}

def validate_product_source(product, official_sources_only=True):
 source=product.get("source",{}); kind=source.get("source_type")
 if kind=="mock_fixture": return {"eligible":True,"reason":"mock_fixture"}
 if not official_sources_only: return {"eligible":True,"reason":"policy_disabled"}
 url=source.get("product_url"); domain=source.get("official_domain")
 valid=kind=="brand_official" and source.get("official_domain_verified") is True and bool(domain and url) and urlparse(url).hostname==domain
 return {"eligible":valid,"reason":"official_source_valid" if valid else "invalid_official_provenance"}

def recommend_products(shopping_spec, provider: ProductProvider, limit=3):
 if not isinstance(limit,int) or not 1<=limit<=5: return {"products":[],"warnings":["invalid_limit"]}
 results=[]; warnings=[]
 for p in provider.search(shopping_spec):
  provenance=validate_product_source(p,shopping_spec.get("source_policy",{}).get("official_sources_only",True))
  if not provenance["eligible"]: continue
  brands=shopping_spec.get("brand_preferences",{}); source=p.get("source",{}); brand=p.get("brand") or source.get("brand")
  if brand in brands.get("avoid",[]): continue
  budget=shopping_spec.get("budget",{}); price=p.get("price",{})
  if budget.get("max_price") is not None:
   if price.get("currency")!=budget.get("currency"):
    if "currency_mismatch" not in warnings: warnings.append("currency_mismatch")
    continue
   if price.get("amount",10**9)>budget["max_price"]: continue
  size_constraints=shopping_spec.get("size_constraints",{})
  requested_sizes=size_constraints.get("sizes",[])
  if requested_sizes and p.get("sizes") and not set(requested_sizes)&set(p["sizes"]): continue
  pref=shopping_spec.get("preferred",{}); attr=sum(bool(set(p.get(k,[] if k!="silhouettes" else [])) & set(pref.get({"colors":"colors","materials":"materials"}.get(k,k),[]))) for k in ("colors","materials"))
  silhouette=p.get("silhouette"); attr+= bool(silhouette in pref.get("silhouettes",[])) if pref.get("silhouettes") else 0
  signals={"attribute_match":attr/3 if attr else .5,"style_match":_overlap(shopping_spec.get("style_modes",[]),p.get("style_tags",[])),"occasion_match":_overlap(shopping_spec.get("occasion",[]),p.get("occasion_tags",[])),"budget_match":1.0,"size_availability":1.0 if requested_sizes and set(requested_sizes)&set(p.get("sizes",[])) else None,"wardrobe_compatibility":.8,"feature_match":.8}
  score=sum(WEIGHTS[k]*v for k,v in signals.items() if v is not None)+(.03 if brand in brands.get("preferred",[]) else 0)
  tradeoffs=[];
  if pref.get("materials") and not set(p.get("materials",[]))&set(pref["materials"]): tradeoffs.append("Preferred material is not present.")
  if shopping_spec.get("shopping_region") and source.get("shopping_region")!=shopping_spec["shopping_region"]: tradeoffs.append("region_mismatch")
  results.append({"product":p,"product_match_score":score,"match_signals":signals,"reasons":["Structured attributes were compared against the shopping specification."],"tradeoffs":tradeoffs})
 results.sort(key=lambda x:x["product_match_score"],reverse=True)
 for i,r in enumerate(results[:limit],1): r["rank"]=i
 if not results: warnings.append("no_matching_products")
 return {"products":results[:limit],"warnings":warnings}
def _overlap(a,b): return 1.0 if set(a)&set(b) else .5
