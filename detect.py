#!/usr/bin/env python3
# ai-tell-taxonomy.md S1/S2 + weekly-capture 스킬 금지목록 기반 탐지기
import re,sys,statistics as st
RULES=[
 # (ID, 심각도, 설명, 정규식)
 ("A-1","S1","'~에 대해(서)'",r'에\s*대[해한]'),
 ("A-2","S1","'~를 통해' 남발",r'[를을]\s*통[해하]'),
 ("A-3","S1","'~에 있어서'",r'에\s*있어서?\b'),
 ("A-7","S1","'가지고 있다'",r'가지고\s*있'),
 ("A-8","S1","이중 피동 '되어진/보여진'",r'되어진|보여진|판단되어'),
 ("A-16","S1","대명사 '그/그녀/그들' 3회+",r'\b그(녀|들|것)\b'),
 ("C-5","S1","이모지 남발(3개+)",r'(?s)[✅🔥🚀💡📌⚡️👉🎯🎁📞📧📅].*?[✅🔥🚀💡📌⚡️👉🎯🎁📞📧📅].*?[✅🔥🚀💡📌⚡️👉🎯🎁📞📧📅]'),
 ("C-11","S1","연결어미 직후 쉼표",r'(?:[^,\s]{3}[고며]|[^,\s]{2}(?:지만|아서|어서)),'),
 ("D-1","S1","결산 피벗 '결론적으로/요약하면'",r'결론적으로|요약하면|요약하자면|이를\s*통해'),
 ("D-2","S1","'시사하는 바가 크다/주목할 만하다'",r'시사하는\s*바|주목할\s*만'),
 ("D-3","S1","'본질적으로/핵심적으로'",r'본질적으로|핵심적으로'),
 ("D-4","S1","hype 어휘",r'파격적|압도적|획기적|다채로운|진정한|자리매김|혁신적'),
 ("D-5","S1","의인화 추상 주어",r'(기술|시대|데이터|숫자|경험|성장|혁신)[은는이가][^.\n]{0,24}(묻|부르|말해|알려|가르쳐|서거든|서는|이깁니|답한)'),
 ("D-6","S1","결말 공식 '~할 때다/해야 한다'",r'할\s*때[다라]|해야\s*한다\.|지금이야말로'),
 ("D-8","S1","과장된 의의 부여",r'이정표|새\s*지평|산물|상징적'),
 ("H-1","S1","문두 접속사 5회+",r'(?m)^\s*(또한|따라서|즉|나아가|게다가|더불어|한편)[ ,]'),
 ("H-3","S1","메타 진입 '이는/이 점에서'",r'(?m)(^|\s)이는\s|이\s*점에서|이\s*관점에서'),
 ("I-1","S1","'~인 것이다/한 것이다'",r'[인한]\s*것이다|것입니다\.'),
 ("G-1","S2","헤징 '~할 수 있습니다'",r'[할수]\s*수\s*(있습니다|있다)'),
 ("F-1","S2","정도부사",r'매우|굉장히|상당히|꽤나|너무나'),
 ("X-1","S1","대조 프레이밍 'A가 아니라 B'",r'(?:게|것[이은]?|[이가])\s*아니라|아니고[,\s]|[이가]\s*아닌\s|대신\s\S+입니다'),
 ("X-2","S1","수사 질문 자답",r'왜[일까요?]*\?\s*(바로|그건)'),
 ("X-3","S1","3연속 열거",r'\w+하고,\s*\w+하고,\s*\w+'),
 ("X-4","S1","일반형 참여 유도(구체 질문은 허용)",r'어떻게\s*생각하시|함께\s*(성장|만들)|좋아요와?\s*공유|많은\s*관심|댓글\s*남겨'),
 ("X-5","S1","형식 맺음 '핵심은/중요합니다'",r'핵심은\s|중요합니다\.|기억하세요'),
 ("X-6","S2","em dash 연결",r'[^-]—[^-]'),
 ("X-7","S2","버즈워드",r'인사이트|레버리지|시너지|임팩트|게임\s*체인저|패러다임|최적화|고도화|극대화'),
 ("X-8","S1","가짜 구체성 '다들/대부분'",r'다들\s|대부분(은|의)\s|사람들은\s'),
 ("X-9","S2","꾸민 친밀 '솔직히/사실은'",r'솔직히\s*말하면|놀랍게도|사실은요'),
 ("X-10","S1","격언·아포리즘(추상주어+보장/결정)",r'(정교함|완벽함|속도|크기|노력|과정|구조)[이은는]\s*\S{0,12}[을를]?\s*(보장|결정|만든다|대신하)'),
 ("X-11","S1","구체 없는 단문 격언",r'(?m)^[^0-9\n]{8,34}(거든요|법이다|뿐이다|이다)\.?$'),
]
def strip_quotes(t):
    # taxonomy Do-NOT: 직접 인용은 탐지 제외.
    # 큰따옴표, 마크다운 백틱 코드 스팬, 코드 블록, 표 구분선을 공백으로 치환한다.
    blank = lambda m: " " * len(m.group(0))
    t = re.sub(r'```.*?```', blank, t, flags=re.S)
    t = re.sub(r'`[^`\n]{1,160}`', blank, t)
    t = re.sub(r'"[^"\n]{1,160}"', blank, t)
    t = re.sub(r'(?m)^\s*>.*$', blank, t)   # 마크다운 인용블록
    # 구조 레이블 위치의 이모지는 장식이 아니다 (헤딩·볼드·리스트 선두)
    t = re.sub(r'(?m)^(\s*(?:[-*+]\s*)?(?:\*\*)?)[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]+',
               lambda m: m.group(1)+" ", t)
    return t

def run(txt,label):
    txt=strip_quotes(txt)
    hits=[]
    for rid,sev,desc,pat in RULES:
        for m in re.finditer(pat,txt):
            hits.append((rid,sev,desc,m.group(0).strip()[:28]))
    s1=[h for h in hits if h[1]=="S1"]; s2=[h for h in hits if h[1]=="S2"]
    ko=len(re.findall(r'[가-힣]',txt))
    sents=[x.strip() for x in re.split(r'(?<=[.?!])\s+|\n+',txt) if len(x.strip())>8]
    L=[len(x) for x in sents]
    print(f"\n{'='*62}\n{label}  (한글 {ko}자 / 문장 {len(L)}개)")
    print(f"  S1 {len(s1)}건   S2 {len(s2)}건   1만자당 {(len(s1)+len(s2))/max(ko,1)*10000:.0f}")
    if L: print(f"  리듬 stdev {st.pstdev(L):.1f}  (E-1: 8 미만이면 S2)  최단 {min(L)} 최장 {max(L)}")
    seen=set()
    for rid,sev,desc,ex in hits:
        k=(rid,ex)
        if k in seen: continue
        seen.add(k); print(f"    [{sev}] {rid:4s} {desc:28s} <- \"{ex}\"")
    return len(s1),len(s2)
def speech_level(txt):
    import re
    txt=strip_quotes(txt)   # S1/S2 와 같은 기준으로 인용·코드 제외
    hae = len(re.findall(r'([가-힣]요|죠)[.?!\n]', txt))   # 해요체: '요' 종결 일반 + '죠'
    nida= len(re.findall(r'니다[.?!\n]', txt))
    da  = len(re.findall(r'(?<!니)[다][.!\n]', txt))
    tot = hae+nida+da
    if tot==0: return None
    mix = tot - max(hae,nida,da)
    return hae,nida,da,mix,tot

if __name__=="__main__":
    t=open(sys.argv[1],encoding='utf-8').read()
    run(t,sys.argv[2] if len(sys.argv)>2 else sys.argv[1])
    # E-2: 동일 종결어미 4문장 연속 = S2.
    # 룰북 처방이 "종결어미 다양화"이므로 어미의 동일성을 본다. 합니다체도 대상이다.
    # ('습니다/합니다/입니다/아닙니다' 는 서로 다른 어미이고, 섞으면 통과한다.
    #  합니다체는 구조적으로 못 피한다는 주장은 반례로 반증됐다.)
    ends=re.findall(r'([가-힣]{2,4})[.?!](?:\s|$)', t)
    sfx=[e[-3:] for e in ends]
    best=cur=1 if sfx else 0; which=sfx[0] if sfx else ''
    for i in range(1,len(sfx)):
        cur = cur+1 if sfx[i]==sfx[i-1] else 1
        if cur>best: best,which = cur,sfx[i]
    if sfx:
        v = best>=4
        print(f"  E-2 동일 종결어미 최대 연속: {best}회 ('{which}')" + (" <= S2 위반(4회+)" if v else " (4회 미만 정상)"))
    sl=speech_level(t)
    if sl:
        hae,nida,da,mix,tot=sl
        names={'hae':'해요체','nida':'합니다체','da':'-다체'}
        dom=max([('hae',hae),('nida',nida),('da',da)],key=lambda x:x[1])
        print(f"  말투: 해요체 {hae} / 합니다체 {nida} / -다체 {da}  -> 주 말투 {names[dom[0]]}, 혼용 {mix}건 (0이어야 함)")
