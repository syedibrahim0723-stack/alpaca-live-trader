"""Topic modelling over recent headlines.

Every few minutes the last 24h of stories are vectorised with TF-IDF and
factorised with NMF. Each story gets its strongest topic; Claude (when a key
is set) turns each topic's top terms into a readable label. Stories that
arrive between rebuilds are assigned with the fitted model straight away.
"""
from __future__ import annotations

import logging
import math
import threading
import time

import numpy as np
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer

log = logging.getLogger("news_radar.topics")

EXTRA_STOP = {
    "inc", "corp", "corporation", "company", "ltd", "plc", "llc", "shares", "stock", "stocks",
    "announces", "announced", "reports", "report", "says", "said", "today", "new", "news",
    "nasdaq", "nyse", "com", "www", "http", "https", "press", "release", "pr", "newswire",
    "globenewswire", "businesswire", "benzinga", "filer", "form",
}

MIN_DOCS = 12


class TopicModel:
    def __init__(self):
        self.vectorizer: TfidfVectorizer | None = None
        self.nmf: NMF | None = None
        self.topic_ids: list[int] = []
        self.lock = threading.Lock()

    def fit(self, docs: list[str]) -> tuple[np.ndarray, list[list[str]]] | None:
        if len(docs) < MIN_DOCS:
            return None
        from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

        vec = TfidfVectorizer(
            stop_words=list(ENGLISH_STOP_WORDS | EXTRA_STOP),
            max_df=0.5,
            min_df=2,
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9\-]{1,}\b",
            max_features=8000,
        )
        try:
            X = vec.fit_transform(docs)
        except ValueError:
            return None
        if X.shape[1] < 10:
            return None
        k = int(max(3, min(12, round(math.sqrt(len(docs) / 2)))))
        k = min(k, X.shape[0] - 1, X.shape[1] - 1)
        nmf = NMF(n_components=k, init="nndsvda", random_state=0, max_iter=400)
        W = nmf.fit_transform(X)
        terms = vec.get_feature_names_out()
        top_terms = [[terms[i] for i in comp.argsort()[::-1][:8]] for comp in nmf.components_]
        with self.lock:
            self.vectorizer, self.nmf = vec, nmf
        return W, top_terms

    def assign(self, text: str) -> int | None:
        """Index of the best topic for one new story, or None."""
        with self.lock:
            if not self.vectorizer or not self.nmf or not self.topic_ids:
                return None
            w = self.nmf.transform(self.vectorizer.transform([text]))[0]
        if w.max() < 0.02:
            return None
        return self.topic_ids[int(w.argmax())]


def doc_text(row: dict) -> str:
    return f"{row['headline']}. {(row.get('summary') or '')[:300]}"


async def rebuild_topics(db, model: TopicModel, classifier=None) -> list[dict]:
    """Refit topics on the last 24h and store them. Returns the topic list."""
    import asyncio

    rows = db.query(
        "SELECT id, headline, summary FROM news WHERE first_seen >= ? ORDER BY first_seen DESC LIMIT 1500",
        (time.time() - 86400,),
    )
    docs = [doc_text(r) for r in rows]
    fitted = await asyncio.to_thread(model.fit, docs)
    if not fitted:
        return list_topics(db)
    W, top_terms = fitted
    assign = W.argmax(axis=1)
    strong = W.max(axis=1) >= 0.02

    clusters = []
    for t, terms in enumerate(top_terms):
        members = [rows[i] for i in np.where((assign == t) & strong)[0]]
        clusters.append({"id": t, "terms": terms, "size": len(members),
                         "samples": [m["headline"] for m in members[:6]]})

    labels: dict[int, str] = {}
    if classifier is not None:
        try:
            labels = await classifier.label_topics(
                [{"id": c["id"], "top_terms": c["terms"], "sample_headlines": c["samples"]}
                 for c in clusters if c["size"]]
            )
        except Exception as e:  # noqa: BLE001 - labelling is best-effort
            log.warning("topic labelling failed: %s", e)

    now = time.time()
    db.execute("DELETE FROM topics")
    db.executemany(
        "INSERT INTO topics(id, label, terms, size, updated) VALUES(?,?,?,?,?)",
        [(c["id"], labels.get(c["id"]) or " · ".join(c["terms"][:3]), ", ".join(c["terms"]), c["size"], now)
         for c in clusters],
    )
    db.execute("UPDATE news SET topic_id=NULL WHERE first_seen >= ?", (now - 86400,))
    db.executemany(
        "UPDATE news SET topic_id=? WHERE id=?",
        [(int(assign[i]), rows[i]["id"]) for i in range(len(rows)) if strong[i]],
    )
    with model.lock:
        model.topic_ids = [c["id"] for c in clusters]
    return list_topics(db)


def list_topics(db) -> list[dict]:
    return db.query("SELECT id, label, terms, size, updated FROM topics WHERE size > 0 ORDER BY size DESC")
