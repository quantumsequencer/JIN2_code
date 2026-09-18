// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Data
{
    using System.Text.Json.Serialization;

    /// <summary>
    /// 動作環境定義（読み取り専用）
    /// </summary>
    internal class AppConfig
    {
        // [A1] α機ノイズ対策前の回路での定数

        // ナノギャップ生成モード（Bias 電圧 0.1V）=> 測定可能範囲 -58.750uA ～ 58.750uA
        private const int    A1RheostatValueInLowMode = 2;                                                // 3段目 帰還抵抗 AD5270BRMZ-20-RL7 のレジスタ設定
        private const double A13rdRfInLowMode         = 20.0 * 1.0e+3 * A1RheostatValueInLowMode / 1024;  // 3段目 帰還抵抗 [Ω]
        private const double A1TIAGainInLowMode       = 51.0 * 1.0e+3;                                    // 1段目 TIA Gain           = 51kΩ [V/A]
        private const double A12ndGainInLowMode       = 120.0 / 100.0;                                    // 2段目 反転増幅回路 Gain   = 120Ω / 100Ω [V/V]
        private const double A13rdGainInLowMode       = 1 + (A13rdRfInLowMode / 100.0);                   // 3段目 非反転増幅回路 Gain = 1 + 約39Ω / 100Ω [V/V]
        private const double A1TotalGainInLowMode     = A1TIAGainInLowMode * A12ndGainInLowMode * A13rdGainInLowMode;
        private const double A1ValuePerVoltInLowMode  = (double)(1L << 32) / 10;                                        // 1V の ADC 検出値         AD Unit_e [LSB/V] = 2^32 [LSB] / 10[V]
        private const double A1ValuePerMicroAmpereInLowMode = A1ValuePerVoltInLowMode * A1TotalGainInLowMode * 1.0e-6;  // 1uA に相当する ADC 検出値 AD Unit_i [LSB/A] = AD Unit_e [LSB/V] * Gain [V/A]

        // 電流計測モード（Bias 電圧 0.1V）=> 測定可能範囲 -578.35pA ～ 578.35pA
        private const int    A1RheostatValueInHighMode = 15;                                                 // 3段目 帰還抵抗 AD5270BRMZ-20-RL7 のレジスタ設定
        private const double A13rdRfInHighMode         = 20.0  * 1.0e+3 * A1RheostatValueInHighMode / 1024;  // 3段目 帰還抵抗 [Ω]
        private const double A1TIAGainInHighMode       = 100.0 * 1.0e+6;                                     // 1段目 TIA Gain           = 100MΩ [V/A]
        private const double A12ndGainInHighMode       = 2.2   * 1.0e+3 / 100.0;                             // 2段目 反転増幅回路 Gain   = 2.2kΩ / 100Ω [V/V]
        private const double A13rdGainInHighMode       = 1 + (A13rdRfInHighMode / 100.0);                    // 3段目 非反転増幅回路 Gain = 1 + 約293Ω / 100Ω [V/V]
        private const double A1TotalGainInHighMode     = A1TIAGainInHighMode * A12ndGainInHighMode * A13rdGainInHighMode;
        private const double A1ValuePerVoltInHighMode  = (double)(1L << 32) / 10;                                          // 1V の ADC 検出値         AD Unit_e [LSB/V] = 2^32 [LSB] / 10[V]
        private const double A1ValuePerPicoAmpereInHighMode = A1ValuePerVoltInHighMode * A1TotalGainInHighMode * 1.0e-12;  // 1pA に相当する ADC 検出値 AD Unit_i [LSB/A] = AD Unit_e [LSB/V] * Gain [V/A]

        // [A2] α機ノイズ対策済み回路での定数

        // ナノギャップ生成モード（Bias 電圧 0.1V）=> 測定可能範囲 -50.196uA ～ 50.196uA
        private const int    A2RheostatValueInLowMode = 51;                                               // 2段目 帰還抵抗 ターゲット 990Ω = 20 x 10^3 x (50.688 / 1024) のため 51 を AD5270BRMZ-20-RL7 のレジスタに設定
        private const double A22ndRfInLowMode         = 20.0 * 1.0e+3 * A2RheostatValueInLowMode / 1024;  // 2段目 帰還抵抗 [Ω]
        private const double A2TIAGainInLowMode       = 33.0 * 1.0e+3;                                    // 1段目 TIA         Gain = 33kΩ [V/A]
        private const double A22ndGainInLowMode       = A22ndRfInLowMode / 330.0;                         // 2段目 反転増幅回路 Gain = 約990Ω / 330Ω [V/V]
        private const double A2TotalGainInLowMode     = A2TIAGainInLowMode * A22ndGainInLowMode;
        private const double A2ValuePerVoltInLowMode  = (double)(1L << 32) / 10;                                        // 1V の ADC 検出値         AD Unit_e [LSB/V] = 2^32 [LSB] / 10 [V]
        private const double A2ValuePerMicroAmpereInLowMode = A2ValuePerVoltInLowMode * A2TotalGainInLowMode * 1.0e-6;  // 1uA に相当する ADC 検出値 AD Unit_i [LSB/A] = AD Unit_e [LSB/V] * Gain [V/A]

        // 電流計測モード（Bias 電圧 0.1V）=> 測定可能範囲 -368.66pA ～ 368.66pA
        private const int    A2RheostatValueInHighMode = 97;                                                // 3段目 帰還抵抗 ターゲット 1.9kΩ = 20 x 10^3 x (97.28 / 1024) のため 97 を AD5270BRMZ-20-RL7 のレジスタに設定
        private const double A23rdRfInHighMode         = 20.0 * 1.0e+3 * A2RheostatValueInHighMode / 1024;  // 3段目 帰還抵抗 [Ω]
        private const double A2TIAGainInHighMode       = 10.0 * 1.0e+6;                                     // 1段目 TIA Gain           = 10MΩ [V/A]
        private const double A22ndGainInHighMode       = 6.8  * 1.0e+3 / 100.0;                             // 2段目 反転増幅回路 Gain   = 6.8kΩ / 100Ω [V/V]
        private const double A23rdGainInHighMode       = 1 + (A23rdRfInHighMode / 100.0);                   // 3段目 非反転増幅回路 Gain = 1 + 約1.9kΩ / 100Ω [V/V]
        private const double A2TotalGainInHighMode     = A2TIAGainInHighMode * A22ndGainInHighMode * A23rdGainInHighMode;
        private const double A2ValuePerVoltInHighMode  = (double)(1L << 32) / 10;                                          // 1V の ADC 検出値         AD Unit_e [LSB/V] = 2^32 [LSB] / 10[V]
        private const double A2ValuePerPicoAmpereInHighMode = A2ValuePerVoltInHighMode * A2TotalGainInHighMode * 1.0e-12;  // 1pA に相当する ADC 検出値 AD Unit_i [LSB/A] = AD Unit_e [LSB/V] * Gain [V/A]

        // 重要: 外部からは読み取り専用にしつつ、デシリアライズ時はセット出来るように [JsonInclude] 属性を付けた上で private set とする。

        /// <summary>
        /// Loopback Client の使用有無
        /// </summary>
        [JsonInclude]
        public bool UseLookbackClient { get; private set; } = true;

        /// <summary>
        /// Stub Port の使用有無
        /// </summary>
        [JsonInclude]
        public bool UseStubHostPort { get; private set; } = true;

        /// <summary>
        /// スレッドプールで同時にアクティブにできるスレッド数
        /// </summary>
        [JsonInclude]
        public int MinWorkerThreads { get; private set; } = 12;

        /// <summary>
        /// マルチキャスト（クライアントへの送信）ホスト名/アドレス
        /// </summary>
        [JsonInclude]
        public string PubHost { get; private set; } = "127.0.0.1";

        /// <summary>
        /// マルチキャスト（クライアントへの送信）ポート番号
        /// </summary>
        [JsonInclude]
        public int PubPort { get; private set; } = 55555;

        /// <summary>
        /// マルチキャスト（クライアントへの送信）トピック「Host Port 受信データ」
        /// </summary>
        [JsonInclude]
        public string PubTopicHost { get; private set; } = "Host";

        /// <summary>
        /// マルチキャスト（クライアントへの送信）トピック「Debug Port 受信データ」
        /// </summary>
        [JsonInclude]
        public string PubTopicDebug { get; private set; } = "Debug";

        /// <summary>
        /// マルチキャスト（クライアントへの送信）トピック「Log Port 受信データ」
        /// </summary>
        [JsonInclude]
        public string PubTopicLog { get; private set; } = "Log";

        /// <summary>
        /// アグリゲーション（クライアントからの受信）ホスト名/アドレス
        /// </summary>
        [JsonInclude]
        public string PullHost { get; private set; } = "*";

        /// <summary>
        /// アグリゲーション（クライアントからの受信）ポート番号
        /// </summary>
        [JsonInclude]
        public int PullPort { get; private set; } = 55556;

        /// <summary>
        /// PUB high-water-mark 値
        /// </summary>
        [JsonInclude]
        public int PubHighWatermark { get; private set; } = 100000;

        /// <summary>
        /// SUB high-water-mark 値
        /// </summary>
        [JsonInclude]
        public int SubHighWatermark { get; private set; } = 100000;

        /// <summary>
        /// PUSH high-water-mark 値
        /// </summary>
        [JsonInclude]
        public int PushHighWatermark { get; private set; } = 100000;

        /// <summary>
        /// PULL high-water-mark 値
        /// </summary>
        [JsonInclude]
        public int PullHighWatermark { get; private set; } = 100000;

        /// <summary>
        /// Host Port の最大同期試行回数（この回数連続で受信データに同期マーカーが含まれていない場合エラーログを出力）
        /// </summary>
        [JsonInclude]
        public int HostPortMaxSyncTrialCount { get; private set; } = 100;

        /// <summary>
        /// Host Port の BaudRate 値
        /// </summary>
        [JsonInclude]
        public int HostPortBaudRate { get; private set; } = 921600;

        /// <summary>
        /// Host Port の Read 時のタイムアウト値（ミリ秒）
        /// </summary>
        [JsonInclude]
        public int HostPortReadTimeout { get; private set; } = 1000;

        /// <summary>
        /// Host Port の Write 時のタイムアウト値（ミリ秒）
        /// </summary>
        [JsonInclude]
        public int HostPortWriteTimeout { get; private set; } = 1000;

        /// <summary>
        /// Debug Port の BaudRate 値
        /// </summary>
        [JsonInclude]
        public int DebugPortBaudRate { get; private set; } = 115200;

        /// <summary>
        /// Debug Port の Read 時のタイムアウト値（ミリ秒）
        /// </summary>
        [JsonInclude]
        public int DebugPortReadTimeout { get; private set; } = 1000;

        /// <summary>
        /// Debug Port の Write 時のタイムアウト値（ミリ秒）
        /// </summary>
        [JsonInclude]
        public int DebugPortWriteTimeout { get; private set; } = 1000;

        /// <summary>
        /// Log Port の BaudRate 値
        /// </summary>
        [JsonInclude]
        public int LogPortBaudRate { get; private set; } = 115200;

        /// <summary>
        /// Log Port の Read 時のタイムアウト値（ミリ秒）
        /// </summary>
        [JsonInclude]
        public int LogPortReadTimeout { get; private set; } = 1000;

        /// <summary>
        /// Log Port の Write 時のタイムアウト値（ミリ秒）
        /// </summary>
        [JsonInclude]
        public int LogPortWriteTimeout { get; private set; } = 1000;

        /// <summary>
        /// コントロール履歴の上限数
        /// </summary>
        [JsonInclude]
        public int ControlHistoryUpperLimit { get; private set; } = 1000;

        /// <summary>
        /// Debug Port 送信履歴の上限数
        /// </summary>
        [JsonInclude]
        public int DebugPortTransmitHistoryUpperLimit { get; private set; } = 1000;

        /// <summary>
        /// Debug Port 受信履歴の上限数
        /// </summary>
        [JsonInclude]
        public int DebugPortReceiveHistoryUpperLimit { get; private set; } = 1000;

        /// <summary>
        /// Log Port 受信履歴の上限数
        /// </summary>
        [JsonInclude]
        public int LogPortReceiveHistoryUpperLimit { get; private set; } = 1000;

        /// <summary>
        /// アプリケーションログ履歴の上限数
        /// </summary>
        [JsonInclude]
        public int AppLogHistoryUpperLimit { get; private set; } = 1000;

        /// <summary>
        /// 電流測定値グラフ表示用情報のリングバッファ最大要素数
        /// </summary>
        [JsonInclude]
        public int CurrentGraphRingBufferCapacity { get; private set; } = 10000;  // 10ミリ秒 x 10000 個 = 100秒分

        /// <summary>
        /// 電流測定値グラフ X 軸最小範囲（要素数）
        /// </summary>
        [JsonInclude]
        public int CurrentGraphXAxisMinRange { get; private set; } = 1;  // 10ミリ秒 x 1 個 = 10ミリ秒

        /// <summary>
        /// 電流測定値グラフ X 軸最大範囲（要素数）
        /// </summary>
        [JsonInclude]
        public int CurrentGraphXAxisMaxRange { get; private set; } = 10000;  // 10ミリ秒 x 10000 個 = 100秒

        /// <summary>
        /// ハードウェア測定値グラフ表示用情報のリングバッファ最大要素数
        /// </summary>
        [JsonInclude]
        public int HardwareGraphRingBufferCapacity { get; private set; } = 100000;  // 10ミリ秒 x 100000 個 = 1000秒分

        /// <summary>
        /// ハードウェア測定値グラフ X 軸最小範囲（要素数）
        /// </summary>
        [JsonInclude]
        public int HardwareGraphXAxisMinRange { get; private set; } = 10;  // 10ミリ秒 x 10 個 = 100ミリ秒

        /// <summary>
        /// ハードウェア測定値グラフ X 軸最大範囲（要素数）
        /// </summary>
        [JsonInclude]
        public int HardwareGraphXAxisMaxRange { get; private set; } = 100000;  // 10ミリ秒 x 100000 個 = 1000秒

        /// <summary>
        /// ナノギャップ生成モード 1uA に相当する ADC 検出値
        /// </summary>
        [JsonInclude]
        public double ValuePerMicroAmpereInLowMode { get; private set; } = A2ValuePerMicroAmpereInLowMode;

        /// <summary>
        /// 電流計測モード 1pA に相当する ADC 検出値
        /// </summary>
        [JsonInclude]
        public double ValuePerPicoAmpereInHighMode { get; private set; } = A2ValuePerPicoAmpereInHighMode;

        /// <summary>
        /// 電流測定値グラフの測定値の描画色
        /// </summary>
        [JsonInclude]
        public string CurrentGraphValueColor { get; private set; } = "#2078B5";

        /// <summary>
        /// 電流測定値グラフの中央値の描画色
        /// </summary>
        [JsonInclude]
        public string CurrentGraphMedianColor { get; private set; } = "#FF0E0E";

        /// <summary>
        /// 電流測定値グラフの二乗平均平方根の描画色
        /// </summary>
        [JsonInclude]
        public string CurrentGraphRmsColor { get; private set; } = "#FFB53B";

        /// <summary>
        /// ハードウェア測定値グラフの電流測定値の描画色
        /// </summary>
        [JsonInclude]
        public string HardwareGraphCurrentColor { get; private set; } = "#017C01";

        /// <summary>
        /// ハードウェア測定値グラフのステッピングモーター位置の描画色
        /// </summary>
        [JsonInclude]
        public string HardwareGraphMotorColor { get; private set; } = "#1717FF";

        /// <summary>
        /// ハードウェア測定値グラフのピエゾアクチュエータ位置の描画色
        /// </summary>
        [JsonInclude]
        public string HardwareGraphPiezoColor { get; private set; } = "#FB0E0F";

        /// <summary>
        /// Stub Host Port での Diag データのフレームサイズ選択肢一覧（バイト）
        /// </summary>
        [JsonInclude]
        public int[] StubHostDiagFrameSizeList { get; private set; } = new int[] { 512, 1024, 2048, 4096, 8192 };

        /// <summary>
        /// Stub Host Port での Diag データの既定フレームサイズ（バイト）
        /// </summary>
        [JsonInclude]
        public int StubHostDiagDefaultFrameSize { get; private set; } = 4096;

        /// <summary>
        /// Stub Host Port での Diag データの受信間隔選択肢一覧（ミリ秒）
        /// </summary>
        [JsonInclude]
        public double[] StubHostDiagFrameIntervalList { get; private set; } = new double[] { 1.0, 2.0, 5.0, 10.0, 20.0, 50.0 };

        /// <summary>
        /// Stub Host Port での Diag データの既定受信間隔（ミリ秒）
        /// </summary>
        [JsonInclude]
        public double StubHostDiagDefaultFrameInterval { get; private set; } = 10.0;

        /// <summary>
        /// Stub Debug Port でのコマンドで駆動される非同期処理の処理時間選択肢一覧（ミリ秒）
        /// </summary>
        [JsonInclude]
        public int[] StubDebugExecutionTimeList { get; private set; } = new int[] { 1000, 2000, 5000, 10000, 20000, 30000, 60000 };

        /// <summary>
        /// Stub Debug Port でのコマンド「dd_ep bias」に対する成功時レスポンステキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugDdEpBiasResponseOnSuccess { get; private set; } = "BIAS set complete.";

        /// <summary>
        /// Stub Debug Port でのコマンド「dd_ep ep」に対する成功時レスポンステキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugDdEpEpResponseOnSuccess { get; private set; } = "EP set complete.";

        /// <summary>
        /// Stub Debug Port でのコマンド「mw_ac go0」に対する成功時レスポンステキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugMwAcGo0ResponseOnSuccess { get; private set; } = "Actuator Control for set 0point complete.";

        /// <summary>
        /// Stub Debug Port でのコマンド「sv_info_sender start」に対するレスポンスの Result Code までの部分テキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugSvInfoSenderStartResponseHeader { get; private set; } = "Start complete. result:";

        /// <summary>
        /// Stub Debug Port でのコマンド「sv_info_sender stop」に対するレスポンスの Result Code までの部分テキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugSvInfoSenderStopResponseHeader { get; private set; } = "Stop complete. result:";

        /// <summary>
        /// Stub Debug Port でのコマンド「mcbj set」に対するレスポンスの Result Code までの部分テキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugMcbjSetResponseHeader { get; private set; } = "Setting change : ";

        /// <summary>
        /// Stub Debug Port でのコマンド「asz set」に対するレスポンスの Result Code までの部分テキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugAszSetResponseHeader { get; private set; } = "Setting change : ";

        /// <summary>
        /// Stub Debug Port でのコマンド「mcbj stop」に対するエラー時レスポンステキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugMcbjStopResponseOnError { get; private set; } = "Stop error : ";

        /// <summary>
        /// Stub Debug Port でのコマンド「mcbj fc start」に対するエラー時レスポンステキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugMcbjFcStartResponseHeaderOnError { get; private set; } = "Start error : ";

        /// <summary>
        /// Stub Debug Port でのコマンド「mcbj fc start」で駆動される非同期処理の完了時 Log Port 出力テキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugMcbjFcLogMessageOnCompleted { get; private set; } = "First Cut finish!";

        /// <summary>
        /// Stub Debug Port でのコマンド「mcbj fc start」で駆動される非同期処理の中止時 Log Port 出力テキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugMcbjFcLogMessageOnCanceled { get; private set; } = "First Cut canceld!";  // F/W と合わせるため、Typo は直さない。

        /// <summary>
        /// Stub Debug Port でのコマンド「mcbj targeting start」に対するエラー時レスポンステキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugMcbjTargetingStartResponseHeaderOnError { get; private set; } = "Targeting Start error : ";

        /// <summary>
        /// Stub Debug Port でのコマンド「mcbj targeting start」で駆動される非同期処理の完了時 Log Port 出力テキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugMcbjTargetingLogMessageOnCompleted { get; private set; } = "Targeting finished.";

        /// <summary>
        /// Stub Debug Port でのコマンド「mcbj targeting start」で駆動される非同期処理の中止時 Log Port 出力テキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugMcbjTargetingLogMessageOnCanceled { get; private set; } = "Targeting canceled.";

        /// <summary>
        /// Stub Debug Port でのコマンド「mcbj mt start」に対するエラー時レスポンステキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugMcbjMtStartResponseHeaderOnError { get; private set; } = "MotorTraining Start error : ";

        /// <summary>
        /// Stub Debug Port でのコマンド「mcbj mt start」で駆動される非同期処理の完了時 Log Port 出力テキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugMcbjMtLogMessageOnCompleted { get; private set; } = "Actuator Training(Motor) end!";

        /// <summary>
        /// Stub Debug Port でのコマンド「mcbj mt start」で駆動される非同期処理の中止時 Log Port 出力テキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugMcbjMtLogMessageOnCanceled { get; private set; } = "Actuator Training(Motor) canceld!";  // F/W と合わせるため、Typo は直さない。

        /// <summary>
        /// Stub Debug Port でのコマンド「mcbj pt start」に対するエラー時レスポンステキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugMcbjPtStartResponseHeaderOnError { get; private set; } = "PiezoTraining Start error : ";

        /// <summary>
        /// Stub Debug Port でのコマンド「mcbj pt start」で駆動される非同期処理の完了時 Log Port 出力テキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugMcbjPtLogMessageOnCompleted { get; private set; } = "Actuator Training(Piezo) end!";

        /// <summary>
        /// Stub Debug Port でのコマンド「mcbj pt start」で駆動される非同期処理の中止時 Log Port 出力テキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugMcbjPtLogMessageOnCanceled { get; private set; } = "Actuator Training(Piezo) canceld!";  // F/W と合わせるため、Typo は直さない。

        /// <summary>
        /// Stub Debug Port でのコマンド「mcbj ac start」に対するエラー時レスポンステキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugMcbjAcStartResponseHeaderOnError { get; private set; } = "AutoCut Start error : ";

        /// <summary>
        /// Stub Debug Port でのコマンド「mcbj ac start」で駆動される非同期処理の完了時 Log Port 出力テキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugMcbjAcLogMessageOnCompleted { get; private set; } = "End.";

        /// <summary>
        /// Stub Debug Port でのコマンド「mcbj ac start」で駆動される非同期処理の中止時 Log Port 出力テキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugMcbjAcLogMessageOnCanceled { get; private set; } = "End. Canceled.";

        /// <summary>
        /// Stub Debug Port でのコマンド「mcbj cal start」に対するエラー時レスポンステキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugMcbjCalStartResponseHeaderOnError { get; private set; } = "Calibration Start error : ";

        /// <summary>
        /// Stub Debug Port でのコマンド「mcbj cal start」で駆動される非同期処理の完了時 Log Port 出力テキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugMcbjCalLogMessageOnCompleted { get; private set; } = "Calibration end!";

        /// <summary>
        /// Stub Debug Port でのコマンド「mcbj cal start」で駆動される非同期処理の中止時 Log Port 出力テキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugMcbjCalLogMessageOnCanceled { get; private set; } = "Calibration canceld!";  // F/W と合わせるため、Typo は直さない。

        /// <summary>
        /// Stub Debug Port でのコマンド「asz eg start」に対するエラー時レスポンステキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugAszEgStartResponseHeaderOnError { get; private set; } = "Start error : ";

        /// <summary>
        /// Stub Debug Port でのコマンド「asz eg start」で駆動される非同期処理の完了時 Log Port 出力テキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugAszEgLogMessageOnCompleted { get; private set; } = "ExpandGap finished.";

        /// <summary>
        /// Stub Debug Port でのコマンド「asz eg start」で駆動される非同期処理の中止時 Log Port 出力テキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugAszEgLogMessageOnCanceled { get; private set; } = "ExpandGap canceled.";

        /// <summary>
        /// Stub Debug Port でのコマンド「asz hg start」に対するエラー時レスポンステキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugAszHgStartResponseHeaderOnError { get; private set; } = "Start error : ";

        /// <summary>
        /// Stub Debug Port でのコマンド「asz hg start」で駆動される非同期処理の完了時 Log Port 出力テキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugAszHgLogMessageOnCompleted { get; private set; } = "HoldGap finished.";

        /// <summary>
        /// Stub Debug Port でのコマンド「asz hg start」で駆動される非同期処理の中止時 Log Port 出力テキスト
        /// </summary>
        [JsonInclude]
        public string StubDebugAszHgLogMessageOnCanceled { get; private set; } = "HoldGap canceled.";

        /// <summary>
        /// 設定ファイルのファイル名
        /// </summary>
        [JsonInclude]
        public string SettingsFileName { get; private set; } = "settings.json";

        /// <summary>
        /// 記録ディレクトリの自動作成先ディレクトリ名の既定値
        /// </summary>
        [JsonInclude]
        public string DefaultBaseRecordDirectoryName { get; private set; } = "data";

        /// <summary>
        /// ログのトップディレクトリ名の接頭辞
        /// </summary>
        [JsonInclude]
        public string LogTopDirectoryNamePrefix { get; private set; } = "log_";

        /// <summary>
        /// Control Link ログのファイル名
        /// </summary>
        [JsonInclude]
        public string ControlLinkLogFileName { get; private set; } = "control_link.log";

        /// <summary>
        /// Debug Port 送信ログのファイル名
        /// </summary>
        [JsonInclude]
        public string DebugPortTxLogFileName { get; private set; } = "debug_port_tx.log";

        /// <summary>
        /// Debug Port 受信ログのファイル名
        /// </summary>
        [JsonInclude]
        public string DebugPortRxLogFileName { get; private set; } = "debug_port_rx.log";

        /// <summary>
        /// Log Port 受信ログのファイル名
        /// </summary>
        [JsonInclude]
        public string LogPortRxLogFileName { get; private set; } = "log_port_rx.log";

        /// <summary>
        /// Snap 記録のディレクトリ名/ファイル名の接中辞
        /// </summary>
        [JsonInclude]
        public string SnapLogNameInfix { get; private set; } = "snap_";

        /// <summary>
        /// 全値ログのディレクトリ名の接頭辞
        /// </summary>
        [JsonInclude]
        public string FullDataLogDirectoryNamePrefix { get; private set; } = "data_";

        /// <summary>
        /// 全値ログのディレクトリ名の接尾辞（電流値なし）
        /// </summary>
        [JsonInclude]
        public string FullDataLogDirectoryNamePostfixNoCurrent { get; private set; } = "_none";

        /// <summary>
        /// 全値ログのディレクトリ名の接尾辞（ナノギャップ生成モード）
        /// </summary>
        [JsonInclude]
        public string FullDataLogDirectoryNamePostfixLowMode { get; private set; } = "_low";

        /// <summary>
        /// 全値ログのディレクトリ名の接尾辞（電流計測モード）
        /// </summary>
        [JsonInclude]
        public string FullDataLogDirectoryNamePostfixHighMode { get; private set; } = "_high";

        /// <summary>
        /// 全値ログのファイル名の接頭辞
        /// </summary>
        [JsonInclude]
        public string FullDataLogFileNamePrefix { get; private set; } = "data_";

        /// <summary>
        /// 全値ログのファイル名の拡張子
        /// </summary>
        [JsonInclude]
        public string FullDataLogFileNameExtension { get; private set; } = ".txt";

        /// <summary>
        /// 全値ログの1ファイル当たりの最大フレーム数
        /// </summary>
        public int FullDataLogMaxFramesPerFile { get; private set; } = 1000;

        /// <summary>
        /// ハードウェア値ログのファイル名の接頭辞
        /// </summary>
        [JsonInclude]
        public string HardwareLogFileNamePrefix { get; private set; } = "hw_data_";

        /// <summary>
        /// ハードウェア値ログのファイル名の拡張子
        /// </summary>
        [JsonInclude]
        public string HardwareLogFileNameExtension { get; private set; } = ".csv";

        /// <summary>
        /// ハードウェア値ログの時刻列のヘッダーテキスト
        /// </summary>
        [JsonInclude]
        public string HardwareLogColumnHeaderTime { get; private set; } = "Time";

        /// <summary>
        /// ハードウェア値ログの Serial Number 列のヘッダーテキスト
        /// </summary>
        [JsonInclude]
        public string HardwareLogColumnHeaderSerialNumber { get; private set; } = "SerialNumber";

        /// <summary>
        /// ハードウェア値ログのデータ種別列のヘッダーテキスト
        /// </summary>
        [JsonInclude]
        public string HardwareLogColumnHeaderDataType { get; private set; } = "DataType";

        /// <summary>
        /// ハードウェア値ログの Bias 電圧列のヘッダーテキスト
        /// </summary>
        [JsonInclude]
        public string HardwareLogColumnHeaderBias { get; private set; } = "Bias";

        /// <summary>
        /// ハードウェア値ログの電流値列のヘッダーテキスト
        /// </summary>
        [JsonInclude]
        public string HardwareLogColumnHeaderCurrent { get; private set; } = "Current";

        /// <summary>
        /// ハードウェア値ログのステッピングモーター位置列のヘッダーテキスト
        /// </summary>
        [JsonInclude]
        public string HardwareLogColumnHeaderMotor { get; private set; } = "MotorPos";

        /// <summary>
        /// ハードウェア値ログのピエゾアクチュエータ位置列のヘッダーテキスト
        /// </summary>
        [JsonInclude]
        public string HardwareLogColumnHeaderPiezo { get; private set; } = "PiezoPos";

        /// <summary>
        /// ハードウェア値ログの電気泳動正電圧列のヘッダーテキスト
        /// </summary>
        [JsonInclude]
        public string HardwareLogColumnHeaderEpPositive { get; private set; } = "+ep";

        /// <summary>
        /// ハードウェア値ログの電気泳動負電圧列のヘッダーテキスト
        /// </summary>
        [JsonInclude]
        public string HardwareLogColumnHeaderEpNegative { get; private set; } = "-ep";
    }
}
