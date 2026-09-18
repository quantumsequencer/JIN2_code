// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using System;
    using System.Collections.ObjectModel;
    using System.Threading.Tasks;
    using Reactive.Bindings;
    using Sony.Jin.Gateway.Data;
    using Sony.Jin.Shared;

    /// <summary>
    /// StubModel
    /// </summary>
    internal interface IStubHostPortModel
    {
        /// <summary>
        /// Host Port のデータ種別項目一覧を取得する。
        /// </summary>
        ReadOnlyCollection<Item<HostPortDataType>> HostDataTypeItems { get; }

        /// <summary>
        /// Host Port のフレームサイズ項目一覧を取得する。
        /// </summary>
        ReadOnlyCollection<Item<int>> HostFrameSizeItems { get; }

        /// <summary>
        /// Host Port のフレーム間隔項目一覧を取得する。
        /// </summary>
        ReadOnlyCollection<Item<double>> HostFrameIntervalItems { get; }

        /// <summary>
        /// Host Port の選択中のデータ種別項目を取得する。
        /// </summary>
        IReactiveProperty<Item<HostPortDataType>> SelectedHostDataTypeItem { get; }

        /// <summary>
        /// Host Port の選択中のフレームサイズ項目を取得する。
        /// </summary>
        IReactiveProperty<Item<int>> SelectedHostFrameSizeItem { get; }

        /// <summary>
        /// Host Port の選択中のフレーム間隔項目を取得する。
        /// </summary>
        IReactiveProperty<Item<double>> SelectedHostFrameIntervalItem { get; }

        /// <summary>
        /// Host Port の受信フレームの Serial Number を取得する。
        /// </summary>
        IReactiveProperty<uint> HostSerialNumber { get; }

        /// <summary>
        /// Host Port の受信状態を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<bool> HostReceiveState { get; }

        /// <summary>
        /// Host Port 全値ログの使用要否を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<bool> UseHostFullDataLog { get; }

        /// <summary>
        /// Host Port ハードウェア値ログの使用要否を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<bool> UseHostHardwareLog { get; }

        /// <summary>
        /// Host Port Frame 生成器の使用要否を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<bool> UseHostFrameGenerator { get; }

        /// <summary>
        /// Host Port 全値ログのディレクトリを取得する。
        /// </summary>
        IReadOnlyReactiveProperty<string> HostFullDataLogDirectory { get; }

        /// <summary>
        /// Host Port ハードウェアログのファイルパスを取得する。
        /// </summary>
        IReadOnlyReactiveProperty<string> HostHardwareLogFile { get; }

        /// <summary>
        /// Host Port の受信フレーム数を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<int> HostReceiveCount { get; }

        /// <summary>
        /// Host Port の受信内容を講読する。
        /// 注意: Subscribe() 時には送出しない。
        /// </summary>
        /// <param name="callback">コールバック</param>
        /// <returns>講読終了用 IDisposable オブジェクト</returns>
        /// <exception cref="ArgumentNullException">callback が null</exception>
        IDisposable HostSubscribe(Action<ByteSpan> callback);

        /// <summary>
        /// Host Port のデータを送信する。
        /// </summary>
        /// <param name="data">送信データ</param>
        /// <returns>成功時 true、エラー時 false</returns>
        Task<bool> HostTransmitAsync(ByteSpan data);

        /// <summary>
        /// Host Port の受信を開始/停止する。
        /// </summary>
        /// <param name="state">開始の場合 true、停止の場合 false</param>
        void SetHostReceiveState(bool state);

        /// <summary>
        /// Host Port Frame Data の生成元を設定する。
        /// </summary>
        /// <param name="sourceType">生成元種別</param>
        /// <returns>成功時 true、エラー時 false</returns>
        bool SetHostFrameSource(HostPortFrameSourceType sourceType);

        /// <summary>
        /// Host Port 全値ログディレクトリを設定する。
        /// </summary>
        /// <param name="directoryPath">ディレクトリパス</param>
        /// <returns>成功時 true、エラー時 false</returns>
        bool SetHostFullDataLogDirectory(string directoryPath);

        /// <summary>
        /// Host Port ハードウェアログファイルを設定する。
        /// </summary>
        /// <param name="filePath">ファイルパス</param>
        /// <returns>成功時 true、エラー時 false</returns>
        bool SetHostHardwareLogFile(string filePath);

        /// <summary>
        /// Host Port の受信フレーム数を 0 にリセットする。
        /// </summary>
        void ResetHostReceiveCount();
    }
}
