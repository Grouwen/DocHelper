from app.domain.recall_chunk import RecallChunk
from app.graph.hook import node_hook
from app.graph.states.query_state import QueryState

@node_hook
def node_rrf_rerank(state:QueryState):
    hyde_recall_results = state["hyde_recall_results"]
    hybrid_recall_results = state["hybrid_recall_results"]

    k = 60
    scores = {}

    for result_list in [hyde_recall_results,hybrid_recall_results]:
        for rank, recall_chunk in enumerate(result_list, start=1):
            scores[recall_chunk.id] = scores.get(recall_chunk.id, 0) + 1.0 / (k + rank)

    # 按分数降序排序
    rrf_results = [
        {"chunk_id": chunk_id, "rrf_score": score}
        for chunk_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "rrf_results":rrf_results[:20]
    }

if __name__ == '__main__':
    node_rrf_rerank(state=QueryState(
        hybrid_recall_results=[RecallChunk(id=2, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.7084106802940369, source='hybrid'), RecallChunk(id=1, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.6945752501487732, source='hybrid'), RecallChunk(id=10, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.6772339344024658, source='hybrid'), RecallChunk(id=5, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.656222939491272, source='hybrid'), RecallChunk(id=7, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.6498061418533325, source='hybrid'), RecallChunk(id=9, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.6424624919891357, source='hybrid'), RecallChunk(id=4, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.40083444118499756, source='hybrid'), RecallChunk(id=6, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.39506644010543823, source='hybrid'), RecallChunk(id=14, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.3870353698730469, source='hybrid'), RecallChunk(id=11, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.38552847504615784, source='hybrid')],
        hyde_recall_results=[RecallChunk(id=2, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.7134747505187988, source='hyde'), RecallChunk(id=4, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.6893735527992249, source='hyde'), RecallChunk(id=1, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.688888669013977, source='hyde'), RecallChunk(id=10, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.6847517490386963, source='hyde'), RecallChunk(id=5, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.6772749423980713, source='hyde'), RecallChunk(id=9, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.6707894802093506, source='hyde'), RecallChunk(id=7, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.6661633253097534, source='hyde'), RecallChunk(id=6, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.6608680486679077, source='hyde'), RecallChunk(id=8, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.6561576128005981, source='hyde'), RecallChunk(id=14, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.6507939100265503, source='hyde'), RecallChunk(id=11, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.6375494003295898, source='hyde'), RecallChunk(id=13, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.6322826147079468, source='hyde'), RecallChunk(id=12, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.6295211315155029, source='hyde'), RecallChunk(id=17, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.6199248433113098, source='hyde'), RecallChunk(id=3, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.6178586483001709, source='hyde'), RecallChunk(id=16, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.612953245639801, source='hyde'), RecallChunk(id=18, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.6023387908935547, source='hyde'), RecallChunk(id=15, title=None, title_breadcrumb_path=None, content=None, content_breadcrumb_path=None, distance=0.5994768738746643, source='hyde')]
    ))