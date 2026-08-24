import asyncio
from typing import List

from langgraph.runtime import Runtime

from app.domain.recall_chunk import RecallChunk
from app.entity.mysql.chunk import MysqlChunk
from app.graph.context.query_context import QueryGraphContext
from app.graph.node_hook import node_hook
from app.graph.states.query_state import QueryState
from app.test.test_graph import test_query_node


def dynamic_topk(scores,
                 min_threshold=0.0,  # 基础门槛：至少得相关
                 min_gap=1.5,  # 断崖检测
                 max_results=5,  # 硬上限
                 min_results=1,  # 硬下限（至少保留1个）
                 use_std_fallback=True):  # 如果阈值过滤后太少，用标准差兜底
    """
    1. 先按阈值过滤
    2. 如果不够，用标准差兜底
    3. 最后用 gap 截断去噪音
    """
    indexed = list(enumerate(scores))

    # 阈值过滤
    candidates = [(i, s) for i, s in indexed if s > min_threshold]
    candidates.sort(key=lambda x: x[1], reverse=True)

    # 如果阈值过滤后太少，启用兜底
    if len(candidates) < min_results and use_std_fallback:
        import statistics
        mean = statistics.mean(scores)
        std = statistics.stdev(scores) if len(scores) > 1 else 0
        # 降低门槛到 mean + 0.5*std
        fallback_threshold = mean + 0.5 * std
        candidates = [(i, s) for i, s in indexed if s >= fallback_threshold]
        candidates.sort(key=lambda x: x[1], reverse=True)

    # 如果还是不够，取全局 top
    if len(candidates) < min_results:
        candidates = sorted(indexed, key=lambda x: x[1], reverse=True)[:min_results]

    # Gap 截断（在结果内部找断崖）
    result = [candidates[0]] if candidates else []
    for i in range(1, len(candidates)):
        if result[-1][1] - candidates[i][1] > min_gap:
            break
        result.append(candidates[i])
        if len(result) >= max_results:
            break

    return result

def merge_by_breadcrumb(chunks: List[MysqlChunk], content_sep: str = "\n") -> List[MysqlChunk]:
    """
    合并相同title_breadcrumb_path，根据part顺序合并
    :param chunks: mysql返回的chunk列表
    :param content_sep: 每个content以什么连接
    :return: 相同title_breadcrumb_path的chunk
    """
    grouped: dict[str, List[MysqlChunk]] = {}

    for chunk in chunks:
        key = chunk.title_breadcrumb_path
        grouped.setdefault(key, []).append(chunk)

    same_breadcrumb_list = []
    for key, group_chunks in grouped.items():
        sorted_chunks = sorted(group_chunks, key=lambda c: c.part)
        merged_obj = MysqlChunk(
            title_breadcrumb_path=key,
            content=content_sep.join(c.content for c in sorted_chunks)
        )
        same_breadcrumb_list.append(merged_obj)

    return same_breadcrumb_list

@node_hook
async def node_bge_rerank(state:QueryState,runtime:Runtime[QueryGraphContext]):
    """
    对rrf粗排的数据进行精排
    1.将title_breadcrumb_path相同的chunk合并
    2.对落差大的chunk截断
    """
    rrf_results = state["rrf_results"]
    rewritten_query = state["rewritten_query"]
    web_search_results = state.get("web_search_results",[])
    mysql_oper = runtime.context["mysql_oper"]
    reranker_model = runtime.context["reranker_model"]

    try:
        # 获取mysql中chunk数据
        mysql_query_result:List[MysqlChunk] = await mysql_oper.query_chunk_by_id([rrf_result["chunk_id"] for rrf_result in rrf_results])

        # 合并相同title_breadcrumb_path
        same_breadcrumb_list = merge_by_breadcrumb(mysql_query_result)

        # 使用bge-reranker
        query_and_chunk = [[rewritten_query,f"面包屑路径：{result.title_breadcrumb_path}，内容：{result.content}"] for result in same_breadcrumb_list]
        query_and_chunk.extend([[rewritten_query, result.content] for result in web_search_results])
        scores =await asyncio.to_thread(reranker_model.compute_score,query_and_chunk)
    except Exception as e:
        return {
            "cross_encoder_results": []
        }

    # 动态截取topk
    topk = dynamic_topk(scores,0,4,10,5,True)
    cross_encoder_results = []
    for index,score in topk:
        cross_encoder_results.append(query_and_chunk[index][1])

    return {
        "cross_encoder_results":cross_encoder_results
    }

if __name__ == '__main__':
    result = asyncio.run(test_query_node(node_bge_rerank,state=QueryState(
        rewritten_query="帮我看看烫金机的使用方法",
        rrf_results=[{'chunk_id': 2, 'rrf_score': 0.03278688524590164}, {'chunk_id': 1, 'rrf_score': 0.03200204813108039}, {'chunk_id': 10, 'rrf_score': 0.03149801587301587}, {'chunk_id': 4, 'rrf_score': 0.031054405392392875}, {'chunk_id': 5, 'rrf_score': 0.031009615384615385}, {'chunk_id': 7, 'rrf_score': 0.030309988518943745}, {'chunk_id': 9, 'rrf_score': 0.030303030303030304}, {'chunk_id': 6, 'rrf_score': 0.029411764705882353}, {'chunk_id': 14, 'rrf_score': 0.02877846790890269}, {'chunk_id': 11, 'rrf_score': 0.028370221327967807}, {'chunk_id': 8, 'rrf_score': 0.014492753623188406}, {'chunk_id': 13, 'rrf_score': 0.013888888888888888}, {'chunk_id': 12, 'rrf_score': 0.0136986301369863}, {'chunk_id': 17, 'rrf_score': 0.013513513513513514}, {'chunk_id': 3, 'rrf_score': 0.013333333333333334}, {'chunk_id': 16, 'rrf_score': 0.013157894736842105}, {'chunk_id': 18, 'rrf_score': 0.012987012987012988}, {'chunk_id': 15, 'rrf_score': 0.01282051282051282}],
        web_search_results=[]
        # web_search_results=[RecallChunk(id=-1, title='烫金机怎么用？烫金机操作说明书_机器', content='# 烫金机怎么用？烫金机操作说明书\n\n1、接通电源，开要空转和停车试验\n\n2、上好烫金板，加温整理好烫金纸，校板并调好需烫部分间距\n\n3、首件经部门主管确认后方可加工\n\n4、完成后，开机清洁机身和周围的废料烫金工艺由于电化铝箔质量的优劣、规格、型号等都会影响到烫印质量，因此，科学合理选用电化铝箔是提高烫金工艺质量的先决条件。工艺流程烫印准备→装版→垫版→烫印工艺参数的确定→试烫→签样→正式烫印。\n\n烫金机操作规程\n\n1、烫金机组长负责监督烫金机机组人员安全。\n\n2、烫金机作业前，作业人员必须将工作服、工作鞋穿戴整齐，扣紧衣襟和袖口，衣袋内不装容易掉出杂物，不戴手表及各种饰物，衣服口袋严禁放工具、硬币、钢笔、手机、打火机等物品，腰间不准挂钥匙、BP机等物品，以防掉入机器。\n\n3、烫金机开机前，应向烫金机机器的各注油点、润滑点和油箱内加入所需润滑油（润滑脂)。4、未经批准，非本烫金机机组人员不得擅自启动烫金机，操作烫金机机器，助手和学徒应在烫金机机长的指导下工作。\n\n5、烫金机机器启动前，应机身各部位是否有杂物，必须先给信号，前后呼应，确定烫金机机器周围安全方可开烫金机。\n\n6、烫金机机器运转前，确保无关人员在烫金机靠近\n\n7、烫金机每次上、下版前必须检查是否有异物，确保打版螺钉紧固。推板动作要轻，以免损坏烫金机，烫金机运转中，严禁用手接触运动工作面，不准维修和擦拭机器，不准跨越转动部位，要保持烫金机机器防护装置完备。\n\n8、机组人员应按分工严守岗位，时刻注意烫金机机器各部位的运转情况，发现问题立即停机处理，长时间停机时一定要关闭总电源开关。\n\n9、工作场地应保持整洁畅通，地面．工作台、烫金机机器周围无杂物，维修工具、零配件要放在规定位置。 [...] 9、工作场地应保持整洁畅通，地面．工作台、烫金机机器周围无杂物，维修工具、零配件要放在规定位置。\n\n10、 烫金机烫印时要注意：当烫印第一（最后一）张时，机器暂停报警，同时开始手动加（减）压力，加（减）压力后又将继续运行。暂停时，操作人员注意安全。\n\n11、工作时，任何人不准在烫金机机台周围嬉笑、打闹、大声喧哗。\n\n12、工作结束时，关闭烫金机电源，确保烫金机周围要清洁好废纸，没有杂物在机上。\n\n13、烫金机要定期保养和维修机器。返回搜狐，查看更多', distance=0.8993429, source='web_search'), RecallChunk(id=-1, title='数字印刷设备展：烫金机怎么用？烫金机的基本使用方法详解', content='在开始正式使用烫金机之前，需要对烫金机进行调试。首先，将烫金箔放置在烫金机的箔架上，并调整箔架的位置，使其与印刷品的表面对齐。然后，根据印刷品的', distance=0.85216236, source='web_search'), RecallChunk(id=-1, title='全自动烫金机在操作中哪些简单使用方法？ - 公司新闻 -     斯迪克', content='## 新闻资讯\n\n### 全自动烫金机工艺主要原理是什么？\n\n2022-04-09\n\n### 全自动烫金机在操作中哪些简单使用方法？\n\n2022-04-09\n\n### 全自动烫金机速度的快慢受哪些因素影响?\n\n2022-04-09\n\n## 全自动烫金机在操作中哪些简单使用方法？\n\n2022-04-09 16:36:17\n\n\u3000\u3000烫金是指在一定的温度和压力下将电化铝箔烫印到承印物表面的工艺过程图文呈现出强烈的金属光泽，色彩鲜艳夺目、永不褪色。尤其是金银电化铝，以其富丽堂皇、精致高雅的装潢点缀了印刷品表面，增强了印品的艺术性，起到了突出主题的宣传效果。全自动烫金机在操作中哪些简单使用方法?\n\n\u3000\u30001、采用触摸屏设计，易于设定操控条件\n\n\u3000\u30002、可以随意调校送箔长度及跳步次数、金箔利用率高\n\n\u3000\u30003、 采用进口优质电控原件，性能稳定可靠\n\n\u3000\u30004、 工作速度达每分钟2500转\n\n\u3000\u30005、特别适宜于细致线条、大面积实地烫金地烫金及纸张压纹\n\n\u3000\u30006、 套印精度高，特别适宜于高精度套印烫金\n\n\u3000\u30007、采用原装机身改装，超长适用寿命;全自动烫金机\n\n\u3000\u30008、设有更换金箔预报警告系统\n\n###### 产品中心\n\n###### 服务支持\n\n###### 关于我们\n\n###### 新闻中心\n\n客服热线\n\n###### 关注我们\n\n微信客服号\n\nCopyright © 2026 深圳市斯迪克自动化设备有限公司\n\n粤ICP备2022060158号\n\n网站地图\n\n### 3162628862 联系在线客服\n\n联系在线客服\n\n服务热线\n\n0755-29755501\n\n关注我们\n\n客服\n\n扫一扫联系我们', distance=0.8036831, source='web_search'), RecallChunk(id=-1, title='烫金机使用注意事项 - 温州杰享机械有限公司', content='在使用烫金机时需注意以下几点： 1.根据不同被烫物选择合适的烫印箔，同时掌握好温度、烫印压力，烫印速度三方面结合，并根据烫印材料、烫印面积的不同做好调整。 2.掌握好', distance=0.78194773, source='web_search'), RecallChunk(id=-1, title='燙金設備全解析：從一塊燙版到數位燙金，金箔是怎麼壓上去的 · MB Packaging', content='✦ 包裝放大鏡 ✦\n\n### 「燙金」是工藝名，不是材料名\n\n很多客戶以為燙金很貴，是因為以為在燙真金。其實現代燙金的成本，主要落在燙版(製版)與機台工時，而不是箔材本身。理解這一點，你就更能判斷一個燙金報價合不合理。\n\n— 02 —\n\n## 一次燙金，機器裡到底發生什麼？\n\n這是全篇最關鍵的一段。把「燙金」這個動作放慢、放大來看，其實是溫度 + 壓力 + 時間三件事，讓一張薄膜上的金屬層，準確地轉印到紙上。先看剖面：\n\n \n\n燙金的本質是「熱壓轉印」：加熱的凸版把電化鋁箔壓進紙面，熱讓膠熔化、把鋁層黏住；版一抬起、箔帶被收走，只有被壓到的圖案留下金。原理圖・MB 編輯室繪製\n\n \n\n那捲看起來像「金色玻璃紙」的箔，其實是一塊精密的五層複合膜。理解它，就懂了為什麼燙金燙的不是金、又為什麼會牢牢黏住：\n\n \n\n電化鋁不是一張紙，而是五層膜。受熱時離型層放手、膠層變黏，把「色層＋鍍鋁層」轉印到紙上；基膜與離型層則隨箔帶被收走。金色其實來自第三層的染色。原理圖・MB 編輯室繪製\n\n \n\n把這套原理放回機台，實際操作大致是這個順序——下面是一條真實燙金線的三個關鍵動作：\n\n燙金機上裝好的電化鋁箔捲，沿著導輥送進 \n\n① 上箔\u3000電化鋁箔捲裝上機台，沿導輥連續送進壓印區。\n\n   燙金前的對位與墊版設定 \n\n② 對位/墊版\u3000調整燙版位置與墊版,讓壓力均勻、套得準。\n\n   燙金壓印進行中,金箔轉印到紙上 \n\n③ 壓印\u3000加熱的燙版壓下,金被轉印到紙上,箔帶往前收走。\n\n上列三張實拍取自同一條燙金線。圖：Flickr・CC BY-SA，點圖見原圖與授權。\n\n❄ 冷知識\u300080–180°C 之間的精準遊戲 [...] — 05 —\n\n## 現代化：免製版的數位燙金\n\n \n\n數位燙金(MGI JETvarnish + iFoil 這類):先用數位噴頭把 UV 光油噴在要燙金處,再讓燙金膜通過加熱滾筒,金只黏在有光油的地方——全程不需傳統燙版。原理圖・MB 編輯室繪製\n\n \n\n▶ 影片：MGI 數位燙金 + 局部 UV\n\n MGI JETvarnish 數位燙金與局部 UV 設備高清畫面 \n\n數位燙金設備外觀更像一台大型數位印刷機——因為它本質上就是用噴墨邏輯在做燙金。點圖看實機。畫面取自 YouTube・僅作介紹說明之用\n\n \n\n❄ 冷知識\u3000可變資料:每一個都能不一樣\n\n傳統燙版一次只能燙同一個圖;數位燙金因為「看檔案」工作,可以做可變資料——一千份喜帖、每張燙不同名字;一批包裝、每個燙不同序號。這在傳統燙金幾乎不可能,卻是個人化包裝與限量編號的利器。\n\n✦ 包裝放大鏡 ✦\n\n### 想先看看燙金效果？數位燙金很適合\n\n要在量產前確認一個燙金 Logo 的位置與感覺,數位燙金讓你不必先花一筆版費就能少量試做。我們會依需求,判斷用數位燙金打樣、還是直接走傳統燙版量產,把錢花在對的地方。\n\n— 06 —\n\n## UV 金是什麼？冷燙與立體 UV 燙金\n\n「UV 金」常讓人混淆,它通常指兩種跟 UV(紫外光固化)有關、但做法完全不同的工藝:冷燙金與立體 UV 燙金。先看冷燙和傳統熱燙差在哪:\n\n \n\n熱燙用「熱」熔膠把箔壓上;冷燙(常被稱為 UV 金)改用印刷把 UV 膠印在紙上、覆上冷燙膜後用 UV 光固化,因此更細緻、還能在銀膜上印出彩色與漸層金屬感。原理圖・MB 編輯室繪製\n\n \n\n▶ 影片：冷燙金原理解說 ▶ 影片：印刷機上的冷燙產線 [...] ❄ 冷知識\u300080–180°C 之間的精準遊戲\n\n燙金的電熱溫度通常落在 80–180°C:面積大、走得快就調高一點。溫度太高,圖文周邊的箔會一起熔掉而「糊版」;太低則熔不透、燙不上或不牢。再加上壓力與停留時間——三者要互相配合,差一點,亮面就會發霧、起泡或掉箔。這也是為什麼老師傅的手感很值錢。\n\n✦ 包裝放大鏡 ✦\n\n### 反光與否，是兩者最大的差距\n\n用 CMYK 或專色「印」出來的金，本質是油墨，不會反光、轉個角度就顯得平。燙金是真正的金屬膜，在燈下會隨角度閃動。要那種「一眼看上去就貴」的金屬光澤，只有燙金做得到。\n\n— 03 —\n\n## 運作模式：平壓平 vs 圓壓圓\n\n懂了壓印原理，機台的分類就很好理解了——差別只在「怎麼壓」。\n\n \n\n平壓平是整版「面接觸」一次壓下，壓力大、品質穩，適合厚紙與禮盒；圓壓圓是滾筒「線接觸」連續滾壓，速度快，適合卷材標籤與大量產線。原理圖・MB 編輯室繪製\n\n \n\n▶ 影片：工廠全自動平壓燙金機 ▶ 影片：卷對卷圓壓燙金機\n\n 工廠全自動平壓燙金模切機高清畫面 \n\n工廠等級的全自動平壓燙金機(常與模切整合):自動送紙、燙金、收紙，一小時上千張，是禮盒量產的主力。點圖看實機。畫面取自 YouTube・僅作介紹說明之用\n\n \n\n❄ 冷知識\u3000「墊版」是燙金的隱形功夫\n\n燙印前師傅會做一道墊版(make-ready):在燙版背後墊上薄紙,把整版各處的壓力調到均勻。紙張本身有厚薄、機台有公差,沒墊好,同一塊版上有的字燙得實、有的發虛。這道看不見的手工,往往才是「工廠級」與「夜市級」的分水嶺。\n\n✦ 包裝放大鏡 ✦\n\n### 厚紙、要飽滿，就靠那一下大壓力\n\n禮盒用厚灰紙板裱貼,需要足夠且均勻的壓力才能讓金箔貼得實、邊緣俐落,甚至一次做出立體燙(燙金＋壓凸)。這正是平壓平的強項,也是高端紙盒幾乎都走工廠全自動平壓的原因。\n\n— 04 —', distance=0.7598145, source='web_search'), RecallChunk(id=-1, title='烫金机操作流程 - 杭州腾隆隆桦智能科技有限公司', content='烫金机操作流程及使用注意方法？ ... ①把烫金纸轻轻放入放料盘，金纸必须能按顺时针方向展开。查验金箔纸的底面（绕在卷筒内侧的一面）是否在打印头下通过', distance=0.7598145, source='web_search'), RecallChunk(id=-1, title='烫金机是用于完成烫金工艺的设备-广州大山铭机械有限公司 - 烫钻机', content='一、工作原理烫金机利用热压转移的原理，将电化铝箔烫印到承印物表面。在合压作用下，电化铝与烫印版、承印物接触，电热板升温使烫印版具有一定的热量，', distance=0.6944897, source='web_search'), RecallChunk(id=-1, title='印刷烫金工艺流程七个步骤，您你看懂了吗！', content='Step 1:在纸张和烫金版中间置入电化铝; Step 2:将烫金版加温到100-150度左右,下压,接触电化铝后,压力作用到纸张上; Step 3:烫金版上的图文内容与纸张完全', distance=0.57837737, source='web_search'), RecallChunk(id=-1, title='谁说烫金机只能是工厂冷冰冰的铁疙瘩？这台小仙女的浪漫打印机我先冲了！🎀_烫金机_淘宝数码网', content='## 金箔不是贴上去的，是“长”出来的\n\n我用它烫过羊皮包带、手工香薰盒、限定版红酒瓶盖，甚至…给我的手账本烫了句“I’m not a girl, I’m a vibe”🌸！你以为是机器压出来的？错！是金箔在温热的模具里，像融化成蜜糖一样，一点点沁进纤维里——不是覆盖，是共生。3040型号的温控精准到小数点后一位，温度低了，金箔粘不牢；高了，纸盒就烧出焦边。而这台机子，从20℃到220℃，像一位温柔的烘焙师，总在你刚想说“再烫一秒”时，自动停住。我试过用手机打光拍它烫完的瞬间，金面像流动的液态星光，连滤镜都不用加，原图直出就是高级感天花板📸\n\n## 谁说小众品牌不能拥有“高定级”设备？\n\n我在小红书上刷到太多姐妹在问：“能不能用普通烫金笔？”——拜托，那叫装饰，不叫创作😭。真正做独立品牌的人，要的是可量产、可复刻、可批量交付的精致感。这台机子不需要专业电工，插电就能用；不需要租厂房，放工作室角落就是你的私人工坊。它不炫技，但它让你的设计说话：当客户打开你那枚烫金的香氛礼盒，指尖抚过那层薄如蝉翼却坚如铠甲的金纹，她不会说“这机器真贵”，她会说：“你真的，很懂我。”\n\n## 我的深夜实验：金箔在皮革上跳的华尔兹\n\n上周三凌晨2点，我对着一条黑色小羊皮肩带，试了第七次烫金。前六次，金箔有气泡、有褶皱、有偏移……第七次，我轻轻按下把手，听见“咻——啪！”——完美！金线如藤蔓般缠绕在皮纹的凹陷里，连皮革的天然纹路都成了它的画框。我哭了，不是因为累，是因为终于有人帮我把“我想做点不一样的”这个念头，变成了可以拿去卖、可以被收藏的实物💎。这不是工具，是创作者的共鸣器。 [...] Slide 1\n\n# 谁说烫金机只能是工厂冷冰冰的铁疙瘩？这台小仙女的浪漫打印机我先冲了！🎀\n\n姐妹们！！！别再把烫金机当成工厂里闷头工作的笨重工具了～这台茗牌烫金机真的美到我尖叫💥！200kg的体重是稳，不是笨，它像一位沉默的高级定制匠人，轻轻一压，金箔就在皮革、纸盒、酒瓶上开出一朵会发光的花🌸。手工品牌、小众香氛、独立设计师…你们的包装梦，它都替你实现得又美又准！不是网红款，但比网红更懂“有质感的生活”。8840不便宜，但买的是你作品被捧在手心的尊严。这哪是机器？是让你的设计开口说话的魔法棒✨\n\n宝子们，还记得上次你收到一款酒盒，烫金的LOGO像月光吻在丝绒上，那一秒心跳漏了半拍吗？😱 那不是印刷，是仪式感在发光。我懂，你不是要一台机器，你是要一个能帮你把“小众审美”变成“别人伸手想摸”的魔法工坊——而这台茗牌烫金机，就是我的新闺蜜🖤\n\n## 不是“重”，是“稳”——200kg的温柔安全感\n\n第一次看到200kg，我：？？？这该不会是工业机器人吧？！但摸上去——哇啊啊！！它真的像一块温热的黑曜石，沉甸甸却毫不刺耳，开机时的气动声是“咻——啪！”的轻柔呼吸，不是轰隆轰隆的噪音暴击🔊。工厂用它是为了效率，但我们用它，是因为它不抖、不晃、不跑偏，哪怕你手抖着压下100次，金箔依旧像被月亮亲吻过那样，边缘干净得能当镜子照✨。它不追求轻巧，它追求“你安心、它听话”的高级感，懂不懂？\n\n## 金箔不是贴上去的，是“长”出来的 [...] 别被“自动烫金”忽悠了，真做包装的都选这台\n\n### 别被“自动烫金”忽悠了，真做包装的都选这台\n\n你真需要一台“全自动烫金机”吗？还是只是被电商页面上的“智能”“高端”“专业级”这些词洗了脑？市面上那些标榜自动化的烫金机，90%都在卖概念。真正的包装厂、烘焙品牌、文创小作坊，要的不是花哨功能，是稳定...\n\n当机器开始为普通物件刻下温度：一台烫金机背后的沉默诗意\n\n### 当机器开始为普通物件刻下温度：一台烫金机背后的沉默诗意\n\n我们总以为工业机器是冰冷的，可当一台浩发机械HF-0098大平面烫金机缓缓压下，金箔在玻璃瓶、空调外壳或亚克力机顶盒上温柔晕开时，我才明白：技术的终点，是让人重新爱上生活中的寻常物。它不只是一台机器，而是一...\n\n姐妹们快看！这台槟榔开包机真的美到我心巴上了✨\n\n### 姐妹们快看！这台槟榔开包机真的美到我心巴上了✨\n\n被槟榔袋折磨到崩溃的姐妹听好了！这台自动充气槟榔开包机真的拯救了我的手指和情绪！不用撕、不用剪、不用猜哪边是口，轻轻一放，它自己“噗——”一声把袋子吹开，\x00封口还顺手给你压得服服帖帖，无痕无损超精致～连...\n\n当一块布料开始诉说心跳：那台沉默的热转印机，像一封未寄出的信\n\n### 当一块布料开始诉说心跳：那台沉默的热转印机，像一封未寄出的信\n\n在这被算法支配的时代，有人悄悄把一台26公斤重的热转印烫画机搬进阁楼，只为在棉布上留下一句只有自己懂的话。AUPLEX AP2519不是冰冷的工业设备，它是一台温柔的印刷诗社，让温度、压力与时间，成为情感的刻痕。...\n\n别被“烫画机”骗了：920块买的不是机器，是情绪的印钞机\n\n### 别被“烫画机”骗了：920块买的不是机器，是情绪的印钞机', distance=0.5492786, source='web_search'), RecallChunk(id=-1, title='CN120828585A - 一种高效转印烫金机及其使用方法 \n        - Google Patents', content='| Publication | Publication Date | Title |\n --- \n| CN120828585B (zh) | 2026-01-13 | 一种高效转印烫金机及其使用方法 |\n| CN120765752B (zh) | 2025-11-14 | 基于视觉定位的切割路径生成系统、切割设备和切割方法 |\n| RU2707796C1 (ru) | 2019-11-29 | Устройство для контроля качества металлических корпусов контейнеров для напитка, содержащих нанесенное изображение |\n| CN110667146B (zh) | 2021-07-16 | 一种薄膜剖面图像的膜厚采集方法 |\n| CN106218230A (zh) | 2016-12-14 | 用于卷材的激光打码模切一体机 |\n| US20220057779A1 (en) | 2022-02-24 | Method and device for intelligently controlling continuous processing of flexible material |\n| JP4132085B2 (ja) | 2008-08-13 | 高速位置決め機構を有するウェブまたはシート供給装置 |\n| CN106695130A (zh) | 2017-05-24 | 高速激光振镜切割机及高速激光振镜切割方法 |\n| CN112719643A (zh) | 2021-04-30 | 表面不规则大曲率薄壁板料快速柔性成形方法及柔性工装 |\n| CN106392664A (zh) | 2017-02-15 | 一种铝焊管动态智能控制连续作业控制方法及生产线 | [...] \\ Cited by examiner, † Cited by third party\n\n| Publication number | Priority date | Publication date | Assignee | Title |\n ---  --- \n| KR100725600B1 (ko) \\ | 2006-09-26 | 2007-06-11 | 윤옥희 | 전사 인쇄기의 필름 권취장치 |\n| CN207028335U (zh) \\ | 2017-07-12 | 2018-02-23 | 中山市新宏业自动化工业有限公司 | 一种烫金模切开窗机 |\n| CN210368298U (zh) \\ | 2019-04-11 | 2020-04-21 | 江苏天成超纤革业有限公司 | 一种箱包底材淋涂烘干一体化产线 |\n| CN110920240A (zh) \\ | 2019-11-26 | 2020-03-27 | 浙江大源机械有限公司 | 一次走纸供多次压印的圆压圆卷筒纸烫印模切机. |\n| CN116604932A (zh) \\ | 2023-07-07 | 2023-08-18 | 种统全 | 一种束口袋烫金生产制造流水线及制造工艺方法 |\n| CN118238505A (zh) \\ | 2024-04-10 | 2024-06-25 | 贵州劲嘉新型包装材料有限公司 | 一种无溶剂pet基膜复合转移联线印刷装置和方法 |\n| CN118683177A (zh) \\ | 2024-06-19 | 2024-09-24 | 常州纳捷机电科技有限公司 | 打印烫金模切功能组合一体机 |\n\n## Cited By (2)\n\n\\ Cited by examiner, † Cited by third party [...] | CN204398478U (zh) | 2015-06-17 | 多功能一体凹印机 |\n| CN119061671A (zh) | 2024-12-03 | 一种高效率服装商标印刷圆点定位套孔裁断工艺 |\n| CN113478883A (zh) | 2021-10-08 | 一种电磁冲压方法及装置 |\n| CN107310133A (zh) | 2017-11-03 | 基于图像处理的bopp薄膜厚度控制方法 |\n| CN121290534A (zh) | 2026-01-09 | 一种多胶层共蓝膜结构的圆刀双异步协同模切工艺及设备 |\n| CN205970408U (zh) | 2017-02-22 | 用于卷材的激光打码模切一体机 |\n| CN102158017B (zh) | 2013-06-05 | 一种长初级直线电机初级铁心片制造方法及冲模 |\n| CN205427583U (zh) | 2016-08-03 | 一种集成式碳纤维自动铺放装置控制系统 |\n| CN100423867C (zh) | 2008-10-08 | 一种卷尺切零机 |\n| CN118744047A (zh) | 2024-10-08 | 偏心辊式破碎机排料粒度控制系统及方法 |\n| CN115185287B (zh) | 2024-12-10 | 一种智能多水下机器人动态避障及围捕控制系统 |\n| CN217168798U (zh) | 2022-08-12 | 一种印刷模切成型装置 |\n| CN118513728A (zh) | 2024-08-20 | 一种基于YOLOv8与ROS2的纸杯盖模具丝网点焊系统及方法 |\n| CN117341281A (zh) | 2024-01-05 | 一种编织袋的精确切割方法 |', distance=0.52773094, source='web_search')]
    )))["cross_encoder_results"]

    print(result)