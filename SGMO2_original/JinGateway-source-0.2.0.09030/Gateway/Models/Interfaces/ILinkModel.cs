// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using System;
    using System.Threading.Tasks;
    using Reactive.Bindings;
    using Sony.Jin.Gateway.Data;
    using Sony.Jin.Shared;

    /// <summary>
    /// LinkModel
    /// </summary>
    internal interface ILinkModel
    {
        /// <summary>
        /// PUB 送信処理の利用可否を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<bool> PubTransmitterAvailable { get; }

        /// <summary>
        /// PULL 受信処理の利用可否を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<bool> PullReceiverAvailable { get; }

        /// <summary>
        /// Application Control 通知を取得する。
        /// 注意: Subscribe() 時には送出しない。
        /// </summary>
        IObservable<ControlType> AppControl { get; }

        /// <summary>
        /// Print Control 通知を取得する。
        /// 注意: Subscribe() 時には送出しない。
        /// </summary>
        IObservable<string> PrintControl { get; }

        /// <summary>
        /// Debug Control 通知を取得する。
        /// 注意: Subscribe() 時には送出しない。
        /// </summary>
        IObservable<string> DebugControl { get; }

        /// <summary>
        /// Host Control 通知を取得する。
        /// 注意: Subscribe() 時には送出しない。
        /// </summary>
        IObservable<ByteSpan> HostControl { get; }

        /// <summary>
        /// 活動を開始する。
        /// View, ViewModel, Model 層のインスタンスは生成され、MainWindow の Load が完了した状態で実行される。
        /// 注意: 起動シーケンスを担い、class MainModel から呼び出されるため、他の箇所から呼び出してはならない。
        /// </summary>
        void Activate();

        /// <summary>
        /// Host Port 受信データを送信する。
        /// </summary>
        /// <param name="data">送信データ</param>
        /// <returns>成功時 true、エラー時 false</returns>
        Task<bool> TransmitHostTopicAsync(ByteSpan data);

        /// <summary>
        /// Debug Port 受信データを送信する。
        /// </summary>
        /// <param name="text">送信テキスト</param>
        /// <returns>成功時 true、エラー時 false</returns>
        Task<bool> TransmitDebugTopicAsync(string text);

        /// <summary>
        /// Log Port 受信データを送信する。
        /// </summary>
        /// <param name="text">送信テキスト</param>
        /// <returns>成功時 true、エラー時 false</returns>
        Task<bool> TransmitLogTopicAsync(string text);
    }
}
