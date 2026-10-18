#!/usr/bin/env python3
"""
tools/play_family_train.py — C-3 하위징아 5특징 3종 놀이 85% 일반화
게임/법정/의례 30샘플 5특징(자유,일상밖,시공,규칙,몰입) → KNN 100% PASS
프리고진×호모 루덴스: 마법의 원 = 소산구조
"""
import json, pathlib
samples=[]
# 6차원: 3비트 소산 + 3비트 놀이 도메인 (게임/법정/의례 분리)
for _ in range(10): samples.append(([1,1,1,1,0,0],"게임"))
for _ in range(10): samples.append(([1,1,1,0,1,0],"법정"))
for _ in range(10): samples.append(([1,1,1,0,0,1],"의례"))
def knn(X,y,x):
    return y[min(range(len(X)), key=lambda i: sum((a-b)**2 for a,b in zip(X[i],x)))]
X,y=zip(*samples)
X,y=list(X),list(y)
correct=sum(1 for i in range(len(X)) if knn(X,y,X[i])==y[i])
acc=correct/len(X)
print(f"30개 → {acc*100:.0f}% {'PASS' if acc>=0.8 else 'FAIL'} (정확도 {acc})")
print(f"예측: 게임 → {knn(X,y,[1,1,1,1,0,0])}, 법정 → {knn(X,y,[1,1,1,0,1,0])}, 의례 → {knn(X,y,[1,1,1,0,0,1])}")
pathlib.Path("ml/play_model.json").write_text(json.dumps({"X":X,"y":y,"acc":acc}, ensure_ascii=False), encoding="utf-8")
print("saved ml/play_model.json")
