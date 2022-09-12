my_strings = [
    "https://open.spotify.com/album/4JAvwK4APPArjIsOdGoJXX?si=DpD0x9A2REWWcn1rjp9dGg",
    "https://open.spotify.com/album/3CCnGldVQ90c26aFATC1PW?si=zWXVidVnSH2LyBOOMOt_KQ",
    "https://open.spotify.com/album/0UMMIkurRUmkruZ3KGBLtG?si=Rnbl3DmMSamIN3EHv-5Qeg",
    "https://open.spotify.com/album/4XLPYMERZZaBzkJg0mkdvO?si=6UQrvjSnQkG7JodQIaJMtw",
    "https://open.spotify.com/album/6Fr2rQkZ383FcMqFyT7yPr?si=yBAsgNk-QvyNN-r3JR9W5w",
    "https://open.spotify.com/album/1yc3Ldus5BkJBVX9mSFMt4?si=Ae_qgnDiRDiSzovQSu7BKA",
    "https://open.spotify.com/album/6mUdeDZCsExyJLMdAfDuwh?si=ontyDbGhR0S9Shb4UvPcnQ",
    "https://open.spotify.com/album/4yP0hdKOZPNshxUOjY0cZj?si=GvmEpcmERs2zVILXapDCHg",
    "https://open.spotify.com/album/0WzOtZBpXvWdNdH7hCJ4qo?si=swFr9HatTbSPCq6aBQnVdw",
    "https://open.spotify.com/album/5wtE5aLX5r7jOosmPhJhhk?si=hIda4i_yS2G0U8msTXriXA",
    "https://open.spotify.com/album/3mH6qwIy9crq0I9YQbOuDf?si=kFzvy3fiSliMaTP1xrDtrg",
    "https://open.spotify.com/album/7gsWAHLeT0w7es6FofOXk1?si=S5cFIl3mRTWU-_xxZQTUnA",
    "https://open.spotify.com/album/0FgZKfoU2Br5sHOfvZKTI9?si=ePu7KyPxSD26UQHgD-X06Q",
    "https://open.spotify.com/album/3BoUxfC7YhxNq3TpOfnRif?si=4JqI3sfNS0SLhh7UUUl1Cw",
    "https://open.spotify.com/album/6wPXUmYJ9mOWrKlLzZ5cCa?si=87T0zNaiRb68U2fvYJAlzg",
    "https://open.spotify.com/album/3DGQ1iZ9XKUQxAUWjfC34w?si=udfdMGgNQlOvnoLJHib_2A",
    "https://open.spotify.com/album/2Y9IRtehByVkegoD7TcLfi?si=nsIqYleHTgWCPxnVX9JgNw",
    "https://open.spotify.com/album/6kf46HbnYCZzP6rjvQHYzg?si=E8iTE1etQaOFwmMyqJ1rUg",
    "https://open.spotify.com/album/5bfpRtBW7RNRdsm3tRyl3R?si=qspdRCVRQsqtve-CThqUpQ",
    "https://open.spotify.com/album/5qENHeCSlwWpEzb25peRmQ?si=43E7OduHRLyJueNMlmRI-w",
    "https://open.spotify.com/album/5lKlFlReHOLShQKyRv6AL9?si=ZfYB2gehR9KFFa9C--rspw",
    "https://open.spotify.com/album/6twKQ0EsUJHVlAr6XBylrj?si=5RSrSxmMQtyZCFy0CD6wfg",
    "https://open.spotify.com/album/1HiN2YXZcc3EjmVZ4WjfBk?si=nHwa7TiUTseShER2gTacxw",
    "https://open.spotify.com/album/6s84u2TUpR3wdUv4NgKA2j?si=MZkZuVsATlOfJs3gXGczcA",
    "https://open.spotify.com/album/4VzzEviJGYUtAeSsJlI9QB?si=ta5KMRfNQ-CDS-vB1QUEeg",
    "https://open.spotify.com/album/7xV2TzoaVc0ycW7fwBwAml?si=UqRBXeLoSV-pbfX3BFG8EQ"
]
for my_string in my_strings:
    split = my_string.partition("com/")[2].partition("/")
    print("?item="+split[0]+"&id="+split[2])
