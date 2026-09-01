    @import url('https://fonts.googleapis.com/css2?family=Goldman:wght@400;700&family=Barlow+Semi+Condensed:wght@400;500;600&display=swap');
    /* Cosmos console vocabulary, lifted from the engine + LM sources:
       fonts GoldmanSansCd_Rg / Goldman-Bold, sizes gui-1..6 = 22/24/28/32/36/52,
       panels background:#1572 and headers #1578, tab strip #333 / back #999.
       Goldman is the same family on Google Fonts; Barlow Semi Condensed stands in
       for GoldmanSansCd_Rg, which is not published there. */
    :root {
      --ground:      #0a1420;
      --panel:       rgba(17, 85, 119, 0.13);   /* #1572 */
      --panel-hi:    rgba(17, 85, 119, 0.33);   /* #1575 */
      --panel-head:  rgba(17, 85, 119, 0.53);   /* #1578 */
      --hair:        rgba(136, 204, 255, 0.16);
      --text:        #ffffff;
      --dim:         #9ab;
      --accent:      #8cf;
      --good:        #8f8;
      --warn:        #ffd76a;
      --alert:       #f55;
      --strip:       #333333;
      --strip-back:  #999999;
      --display: 'Goldman', 'Goldman-Bold', system-ui, sans-serif;
      --body: 'Barlow Semi Condensed', 'GoldmanSansCd_Rg', system-ui, sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0; width: 1920px; height: 1080px; overflow: hidden;
      background-color: var(--ground);
      /* the faint tile field the console paints behind every panel */
      background-image:
        repeating-linear-gradient(90deg, rgba(255,255,255,.018) 0 1px, transparent 1px 160px),
        repeating-linear-gradient(0deg,  rgba(255,255,255,.018) 0 1px, transparent 1px 160px),
        radial-gradient(120% 90% at 22% 8%, rgba(30,72,110,.34), transparent 62%);
      color: var(--text);
      font-family: var(--body);
      font-size: 24px;
      -webkit-font-smoothing: antialiased;
    }
    a { color: var(--accent); text-decoration: none; }
    a:hover { color: #bdf; }

    /* --- the engine tab strip: Layout(20,0,100,3), row-height 35px --------- */
    .strip { position: absolute; left: 20%; top: 0; width: 80%; height: 35px;
             display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); }
    .strip .slot { margin: 1px 0 0 0; }
    .strip .tab  { height: 34px; display: flex; align-items: center; justify-content: center;
                   background: var(--strip); color: #000; font-family: var(--body);
                   font-size: 24px; font-weight: 600; letter-spacing: .02em; }
    .strip .tab.back { background: var(--strip-back); }

    /* --- PADD chrome ------------------------------------------------------- */
    .padd { position: absolute; left: 0; top: 45px; width: 1920px; height: 1035px;
            display: flex; flex-direction: column; }
    .padd-bar { height: 64px; flex: 0 0 auto; display: flex; align-items: center; gap: 24px;
                padding: 0 40px; background: var(--panel-head);
                border-bottom: 1px solid var(--hair); }
    .mark { font-family: var(--display); font-weight: 700; font-size: 32px;
            letter-spacing: .06em; color: var(--text); }
    .mark em { font-style: normal; color: var(--accent); }
    .bar-dim { font-size: 22px; color: var(--dim); letter-spacing: .04em; }
    .bar-right { margin-left: auto; display: flex; align-items: center; gap: 28px; }
    .pill { font-family: var(--display); font-size: 22px; letter-spacing: .10em;
            padding: 4px 14px; color: var(--ground); background: var(--good); }
    .pill.red { background: var(--alert); color: #fff; }

    /* --- app grid ---------------------------------------------------------- */
    .sheet { flex: 1 1 auto; padding: 36px 96px 0 96px; display: flex;
             flex-direction: column; gap: 30px; }
    .group-head { display: flex; align-items: center; gap: 20px; }
    .group-head h2 { margin: 0; font-family: var(--display); font-weight: 700;
                     font-size: 24px; letter-spacing: .18em; color: var(--accent);
                     text-transform: uppercase; }
    .group-head .rule { flex: 1 1 auto; height: 1px; background: var(--hair); }
    .grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 28px; }
    /* sc-if may introduce a wrapper around a tile; make either shape fill its cell. */
    .grid > * { min-width: 0; display: flex; }
    .grid > * > .tile { flex: 1 1 auto; }
    .tile { width: 100%; display: flex; align-items: center; gap: 24px; padding: 26px 28px;
            background: var(--panel); border: 1px solid var(--hair);
            cursor: pointer; text-align: left; color: inherit; font: inherit;
            transition: background .12s, border-color .12s; }
    .tile:hover { background: var(--panel-hi); border-color: rgba(136,204,255,.42); }
    /* icons come from the ePADD sheet, sliced per app - see design/epadd/sheet.html */
    .tile .ico { flex: 0 0 auto; width: 72px; height: 72px; display: block;
                 object-fit: contain; image-rendering: auto; }
    .tile .lbl { min-width: 0; }
    .tile h3 { margin: 0 0 4px 0; font-family: var(--display); font-weight: 700;
               font-size: 32px; line-height: 1.05; letter-spacing: .01em; color: var(--text); }
    .tile p  { margin: 0; font-size: 22px; line-height: 1.2; color: var(--dim); }
    .exit { padding: 0 96px 26px 96px; display: flex; justify-content: flex-end; }
    .exit button { background: none; border: 1px solid var(--hair); color: var(--dim);
                   font-family: var(--display); font-size: 22px; letter-spacing: .12em;
                   padding: 10px 22px; cursor: pointer; }
    .exit button:hover { color: var(--text); border-color: var(--accent); }
