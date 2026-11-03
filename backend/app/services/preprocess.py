import pandas as pd

from app.models.paper import Paper
from app.services.text import clean_text, chinese_words, english_words


# 批量预处理：清洗文本、统计中英文词、判断语种
def preprocess_papers(papers: list[Paper]) -> pd.DataFrame:
    rows = [
        {
            "paper_id": paper.id,
            "title": clean_text(paper.title),
            "abstract": clean_text(paper.abstract),
        }
        for paper in papers
    ]
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # 标题 + 摘要作为标注输入
    df["text"] = (df["title"] + ". " + df["abstract"]).str.strip()
    df = df[df["text"].str.len() > 0].copy()
    if df.empty:
        return df

    # 中英文词数，用于判断语种
    df["zh_tokens"] = df["text"].apply(lambda t: len(chinese_words(t)))
    df["en_tokens"] = df["text"].apply(lambda t: len(english_words(t)))
    df["language"] = df.apply(
        lambda r: "zh" if r["zh_tokens"] >= r["en_tokens"] else "en", axis=1
    )

    return df.drop_duplicates(subset=["text"]).reset_index(drop=True)
