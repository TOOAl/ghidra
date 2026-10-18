"""
memory/vector_store.py — 기억 도서관 (Vector DB)

한 번 분석한 함수는 절대 잊지 않음.
다음에 비슷한 함수를 보면 "아, 그때 그거!" 하고 꺼내줌.
무료 로컬 임베딩 (sentence-transformers) 사용 — API 비용 0.
"""
from pathlib import Path
import json

class VectorMemory:
    def __init__(self, persist_dir="memory/chroma_db", embedding_model="all-MiniLM-L6-v2"):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_model_name = embedding_model
        self._client = None
        self._collection = None
        self._init_db()

    def _init_db(self):
        try:
            import chromadb
            from chromadb.utils import embedding_functions
            self._client = chromadb.PersistentClient(path=str(self.persist_dir))
            # 로컬 임베딩 (무료, 오프라인)
            ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=self.embedding_model_name)
            self._collection = self._client.get_or_create_collection(
                name="ghidra_functions",
                embedding_function=ef
            )
            print(f"[Memory] ChromaDB 로드: {self.persist_dir} ({self._collection.count()}개 기억)")
        except ImportError:
            print("[Memory] chromadb 미설치 — pip install chromadb sentence-transformers 로 활성화")
            print("[Memory] 임시로 JSON 파일 기반 기억으로 동작")
            self._client = None
        except Exception as e:
            print(f"[Memory] 초기화 실패: {e}")
            self._client = None

    def add(self, func_name: str, pseudocode: str, note: str = "", metadata: dict = None):
        """함수 하나를 기억에 저장"""
        doc = f"함수 {func_name}: {note}\n{pseudocode[:1000]}"
        if self._client:
            self._collection.add(
                ids=[func_name],
                documents=[doc],
                metadatas=[metadata or {"func": func_name}]
            )
        else:
            # 폴백: JSONL에 저장
            with open("memory/session.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({"type": "memory_add", "func": func_name, "doc": doc}, ensure_ascii=False) + "\n")
        print(f"[Memory] 기억 저장: {func_name}")

    def add_turn(self, task: str, tool: str, inp: dict, result: dict):
        """매 턴의 결과를 기억에 추가 (자동)"""
        # 간단 구현: decompile 결과만 기억
        if tool == "decompile" and "c_code" in result:
            self.add(inp.get("name", "unknown"), result["c_code"], note=f"Task: {task}")

    def search(self, query: str, k=3) -> dict:
        """유사한 과거 기억 검색"""
        if self._client and self._collection.count() > 0:
            res = self._collection.query(query_texts=[query], n_results=k)
            out = []
            for i, doc in enumerate(res["documents"][0]):
                out.append({
                    "document": doc[:500],
                    "metadata": res["metadatas"][0][i] if res["metadatas"][0] else {},
                    "distance": res["distances"][0][i] if "distances" in res else None
                })
            return {"query": query, "results": out}
        else:
            # 폴백: session.jsonl에서 키워드 검색
            return {"query": query, "results": [
                {"document": "(ChromaDB 미설치) session.jsonl에서 키워드 검색 필요", "metadata": {}}
            ]}

    def count(self) -> int:
        if self._client:
            return self._collection.count()
        return 0
