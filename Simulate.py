import pyupbit
import pandas as pd

def run_backtest(ticker, days=7):
    print(f"🔍 [{ticker}] 지난 {days}일 15분봉 데이터 분석 중...")
    
    # 15분봉 기준 7일치 캔들 개수: 24시간 * 4개 * 7일 = 672개
    df = pyupbit.get_ohlcv(ticker, interval="minute15", count=24 * 4 * days)
    
    if df is None or df.empty:
        print(f"⚠️ {ticker} 데이터를 불러오지 못했습니다.\n")
        return

    # 1. 지표 계산
    df['donchian_upper'] = df['high'].rolling(window=20).max().shift(1)
    df['donchian_lower'] = df['low'].rolling(window=20).min().shift(1)
    df['donchian_mid'] = (df['donchian_upper'] + df['donchian_lower']) / 2

    df['high_14'] = df['high'].rolling(window=14).max()
    df['low_14'] = df['low'].rolling(window=14).min()
    df['willr'] = ((df['high_14'] - df['close']) / (df['high_14'] - df['low_14'])) * -100

    df['vol_ma'] = df['volume'].rolling(window=20).mean()

    # 2. 매수 신호 세팅
    df['buy_signal'] = (df['close'] >= df['donchian_upper']) & (df['willr'] >= -20) & (df['volume'] > df['vol_ma'])

    # 3. 시뮬레이션
    position = 0
    entry_price = 0
    trades = []

    for index, row in df.iterrows():
        if pd.isna(row['donchian_upper']) or pd.isna(row['willr']):
            continue

        if position == 0 and row['buy_signal']:
            position = 1
            entry_price = row['close']
        
        elif position == 1:
            # 매도 조건 3가지
            sell_cond_1 = row['close'] <= (entry_price * 0.97) # -3% 강제 손절
            sell_cond_2 = row['close'] <= row['donchian_mid']  # 중심선 이탈 (추세 꺾임)
            sell_cond_3 = row['willr'] <= -80                  # 모멘텀 소멸

            if sell_cond_1 or sell_cond_2 or sell_cond_3:
                profit_rate = (row['close'] - entry_price) / entry_price * 100
                net_profit_rate = profit_rate - 0.1 # 업비트 왕복 수수료 약 0.1% 차감
                trades.append(net_profit_rate)
                position = 0

    # 현재 포지션이 열려있다면 강제 청산 결과 반영
    if position == 1:
        profit_rate = (df.iloc[-1]['close'] - entry_price) / entry_price * 100
        trades.append(profit_rate - 0.1)

    # 4. 결과 출력
    if len(trades) > 0:
        win_trades = [t for t in trades if t > 0]
        win_rate = (len(win_trades) / len(trades)) * 100
        total_profit = sum(trades)
        
        # 복리 수익률 계산
        compounded = 1.0
        for t in trades:
            compounded *= (1 + t / 100)
        compounded_rate = (compounded - 1) * 100

        print(f"✔️ 총 매매 횟수 : {len(trades)}회 (승리 {len(win_trades)}회 / 패배 {len(trades) - len(win_trades)}회)")
        print(f"✔️ 승률        : {win_rate:.1f}%")
        print(f"✔️ 단순 수익률 : {total_profit:.2f}% (수수료 차감 후)")
        print(f"✔️ 복리 수익률 : {compounded_rate:.2f}%\n")
    else:
        print("✔️ 해당 기간 동안 매수 조건이 충족되지 않았습니다.\n")

print("==========================================")
print("📈 업비트 일주일(7일) 15분봉 백테스팅 결과")
print("==========================================")
run_backtest("KRW-BTC", 7)
run_backtest("KRW-ETH", 7)
