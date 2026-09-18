// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using System;
    using System.Collections.ObjectModel;
    using System.Threading.Tasks;
    using Reactive.Bindings;
    using Sony.Jin.Shared;

    /// <summary>
    /// PortModel
    /// </summary>
    internal interface IPortModel
    {
        /// <summary>
        /// Host Port 一覧を取得する。
        /// </summary>
        ReadOnlyCollection<IPortUnit<ByteSpan>> HostPortUnits { get; }

        /// <summary>
        /// Debug Port 一覧を取得する。
        /// </summary>
        ReadOnlyCollection<IPortUnit<string>> DebugPortUnits { get; }

        /// <summary>
        /// Log Port 一覧を取得する。
        /// </summary>
        ReadOnlyCollection<IPortUnit<string>> LogPortUnits { get; }

        /// <summary>
        /// Host Port の利用可否を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<bool> HostPortAvailable { get; }

        /// <summary>
        /// Debug Port の利用可否を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<bool> DebugPortAvailable { get; }

        /// <summary>
        /// Log Port の利用可否を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<bool> LogPortAvailable { get; }

        /// <summary>
        /// 選択中の Host Port を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<IPortUnit<ByteSpan>> SelectedHostPortUnit { get; }

        /// <summary>
        /// 選択中の Debug Port を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<IPortUnit<string>> SelectedDebugPortUnit { get; }

        /// <summary>
        /// 選択中の Log Port を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<IPortUnit<string>> SelectedLogPortUnit { get; }

        /// <summary>
        /// Host Port 送信通知を取得する。
        /// 注意: Subscribe() 時には送出しない。
        /// </summary>
        IObservable<ByteSpan> HostPortTransmitted { get; }

        /// <summary>
        /// Debug Port 送信通知を取得する。
        /// 注意: Subscribe() 時には送出しない。
        /// </summary>
        IObservable<string> DebugPortTransmitted { get; }

        /// <summary>
        /// Host Port 受信通知を取得する。
        /// 注意: Subscribe() 時には送出しない。
        /// </summary>
        IObservable<ByteSpan> HostPortReceived { get; }

        /// <summary>
        /// Debug Port 受信通知を取得する。
        /// 注意: Subscribe() 時には送出しない。
        /// </summary>
        IObservable<string> DebugPortReceived { get; }

        /// <summary>
        /// Log Port 受信通知を取得する。
        /// 注意: Subscribe() 時には送出しない。
        /// </summary>
        IObservable<string> LogPortReceived { get; }

        /// <summary>
        /// 活動を開始する。
        /// View, ViewModel, Model 層のインスタンスは生成され、MainWindow の Load が完了した状態で実行される。
        /// 注意: 起動シーケンスを担い、class MainModel から呼び出されるため、他の箇所から呼び出してはならない。
        /// </summary>
        void Activate();

        /// <summary>
        /// Host Port を選択状態にする。
        /// </summary>
        /// <param name="portUnit">Port Unit</param>
        /// <returns>成功時 true、エラー時 false</returns>
        bool SetSelectedHostPortUnit(IPortUnit<ByteSpan> portUnit);

        /// <summary>
        /// Debug Port を選択状態にする。
        /// </summary>
        /// <param name="portUnit">Port Unit</param>
        /// <returns>成功時 true、エラー時 false</returns>
        bool SetSelectedDebugPortUnit(IPortUnit<string> portUnit);

        /// <summary>
        /// Log Port を選択状態にする。
        /// </summary>
        /// <param name="portUnit">Port Unit</param>
        /// <returns>成功時 true、エラー時 false</returns>
        bool SetSelectedLogPortUnit(IPortUnit<string> portUnit);

        /// <summary>
        /// Host Port に送信する。
        /// </summary>
        /// <param name="data">データ</param>
        /// <returns>成功時 true、エラー時 false</returns>
        Task<bool> TransmitHostPortUnitAsync(ByteSpan data);

        /// <summary>
        /// Debug Port に送信する。
        /// </summary>
        /// <param name="text">テキスト</param>
        /// <returns>成功時 true、エラー時 false</returns>
        Task<bool> TransmitDebugPortUnitAsync(string text);
    }
}
