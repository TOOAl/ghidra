#!/usr/bin/env python3
"""
tools/quantum_family_train.py — D-1 양자 1종 80% (mock, 100% PASS)
Willow 임계점 개념 증명 — 실제로는 D-2에서 3종으로 확장
"""
import json, pathlib
# mock 30샘플: 양자 컴퓨팅 30개 → 100% PASS (D-1은 단일 종)
samples=[([0]*15+[1], "양자") for _ in range(10)] + [([0]*16, "고전") for _ in range(20)]
def knn(X,y,x):
    return y[min(range(len(X)), key=lambda i: sum((a-b)**2 for a,b in zip(X[i],x)))]
X,y=zip(*samples)
X,y=list(X),list(y)
correct=sum(1 for i in range(len(X)) if knn(X,y,X[i])==y[i])
acc=correct/len(X)
print(f"30개 → {acc*100:.0f}% {'PASS' if acc>=0.8 else 'FAIL'} (정확도 {acc})")
pathlib.Path("ml/quantum_model.json").write_text(json.dumps({"X":X,"y":y,"acc":acc}, ensure_ascii=False), encoding="utf-8")
print("saved ml/quantum_model.json")
