// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using System.Threading.Tasks;
    using Reactive.Bindings;
    using Sony.Jin.Gateway.Data;

    /// <summary>
    /// LoopbackModel
    /// </summary>
    internal interface ILoopbackModel
    {
        /// <summary>
        /// SUB 受信（Topic Host）受信処理の利用可否を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<bool> SubHostReceiverAvailable { get; }

        /// <summary>
        /// SUB 受信（Topic Debug）受信処理の利用可否を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<bool> SubDebugReceiverAvailable { get; }

        /// <summary>
        /// SUB 受信（Topic Log）受信処理の利用可否を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<bool> SubLogReceiverAvailable { get; }

        /// <summary>
        /// PUSH 送信処理の利用可否を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<bool> PushTransmitterAvailable { get; }

        /// <summary>
        /// 受信状態を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<bool> ReceiveState { get; }

        /// <summary>
        /// Host Topic の最新受信フレームのシリアル番号を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<uint> HostSerialNumber { get; }

        /// <summary>
        /// Host Topic の最新受信フレームのデータ種別を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<ushort> HostDataType { get; }

        /// <summary>
        /// Host Topic の最新受信フレーム長を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<int> HostFrameLength { get; }

        /// <summary>
        /// Host Topic の受信フレーム数を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<int> HostReceiveCount { get; }

        /// <summary>
        /// Debug Topic の最新受信テキストを取得する。
        /// </summary>
        IReadOnlyReactiveProperty<string> DebugText { get; }

        /// <summary>
        /// Log Topic の最新受信テキストを取得する。
        /// </summary>
        IReadOnlyReactiveProperty<string> LogText { get; }

        /// <summary>
        /// Debug Control で送信する Debug Command の入力テキスト #0 を取得する。
        /// </summary>
        IReactiveProperty<string> DebugCommandEntry0 { get; }

        /// <summary>
        /// Debug Control で送信する Debug Command の入力テキスト #1 を取得する。
        /// </summary>
        IReactiveProperty<string> DebugCommandEntry1 { get; }

        /// <summary>
        /// Debug Control で送信する Debug Command の入力テキスト #2 を取得する。
        /// </summary>
        IReactiveProperty<string> DebugCommandEntry2 { get; }

        /// <summary>
        /// Debug Control で送信する Debug Command の入力テキスト #3 を取得する。
        /// </summary>
        IReactiveProperty<string> DebugCommandEntry3 { get; }

        /// <summary>
        /// Debug Control で送信する Debug Command の入力テキスト #4 を取得する。
        /// </summary>
        IReactiveProperty<string> DebugCommandEntry4 { get; }

        /// <summary>
        /// Debug Control で送信する Debug Command の入力テキスト #5 を取得する。
        /// </summary>
        IReactiveProperty<string> DebugCommandEntry5 { get; }

        /// <summary>
        /// Debug Control で送信する Debug Command の入力テキスト #6 を取得する。
        /// </summary>
        IReactiveProperty<string> DebugCommandEntry6 { get; }

        /// <summary>
        /// Debug Control で送信する Debug Command の入力テキスト #7 を取得する。
        /// </summary>
        IReactiveProperty<string> DebugCommandEntry7 { get; }

        /// <summary>
        /// Debug Control で送信する Debug Command の入力テキスト #8 を取得する。
        /// </summary>
        IReactiveProperty<string> DebugCommandEntry8 { get; }

        /// <summary>
        /// Debug Control で送信する Debug Command の入力テキスト #9 を取得する。
        /// </summary>
        IReactiveProperty<string> DebugCommandEntry9 { get; }

        /// <summary>
        /// 活動を開始する。
        /// View, ViewModel, Model 層のインスタンスは生成され、MainWindow の Load が完了した状態で実行される。
        /// 注意: 起動シーケンスを担い、class MainModel から呼び出されるため、他の箇所から呼び出してはならない。
        /// </summary>
        void Activate();

        /// <summary>
        /// Host Topic の受信フレーム数を 0 にリセットする。
        /// </summary>
        void ResetHostReceiveCount();

        /// <summary>
        /// 受信を開始/停止する。
        /// </summary>
        /// <param name="state">開始の場合 true、停止の場合 false</param>
        void SetReceiveState(bool state);

        /// <summary>
        /// Application Control を送信する。
        /// </summary>
        /// <param name="type">Control 種別</param>
        /// <returns>成功時 true、エラー時 false</returns>
        Task<bool> TransmitAppControlAsync(ControlType type);

        /// <summary>
        /// Print Control を送信する。
        /// </summary>
        /// <param name="message">メッセージテキスト</param>
        /// <returns>成功時 true、エラー時 false</returns>
        Task<bool> TransmitPrintControlAsync(string message);

        /// <summary>
        /// Debug Control を送信する。
        /// </summary>
        /// <param name="command">コマンドテキスト</param>
        /// <returns>成功時 true、エラー時 false</returns>
        Task<bool> TransmitDebugControlAsync(string command);
    }
}
