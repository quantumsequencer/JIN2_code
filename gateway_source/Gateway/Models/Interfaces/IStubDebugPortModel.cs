// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using System;
    using System.Collections.ObjectModel;
    using System.Threading.Tasks;
    using Reactive.Bindings;
    using Sony.Jin.Shared;

    /// <summary>
    /// StubDebugPortModel
    /// </summary>
    internal interface IStubDebugPortModel
    {
        /// <summary>
        /// Debug Port コマンドに対する Result Code 項目一覧を取得する。
        /// </summary>
        ReadOnlyCollection<Item<sbyte>> DebugResultCodeItems { get; }

        /// <summary>
        /// Debug Port コマンドで駆動される非同期処理の処理時間（ミリ秒）項目一覧を取得する。
        /// </summary>
        ReadOnlyCollection<Item<int>> DebugExecutionTimeItems { get; }

        /// <summary>
        /// Debug Port コマンド「dd_ep bias」に対するレスポンステキストの有無を取得する。
        /// </summary>
        IReactiveProperty<bool> DebugDdEpBiasResult { get; }

        /// <summary>
        /// Debug Port コマンド「dd_ep ep」に対するレスポンステキストの有無を取得する。
        /// </summary>
        IReactiveProperty<bool> DebugDdEpEpResult { get; }

        /// <summary>
        /// Debug Port コマンド「mw_ac go0」に対するレスポンステキストの有無を取得する。
        /// </summary>
        IReactiveProperty<bool> DebugMwAcGo0Result { get; }

        /// <summary>
        /// Debug Port コマンド「sv_info_sender start」に対する選択中の Result Code 項目を取得する。
        /// </summary>
        IReactiveProperty<Item<sbyte>> SelectedDebugSvInfoSenderStartResultCodeItem { get; }

        /// <summary>
        /// Debug Port コマンド「sv_info_sender stop」に対する選択中の Result Code 項目を取得する。
        /// </summary>
        IReactiveProperty<Item<sbyte>> SelectedDebugSvInfoSenderStopResultCodeItem { get; }

        /// <summary>
        /// Debug Port コマンド「mcbj set」に対する選択中の Result Code 項目を取得する。
        /// </summary>
        IReactiveProperty<Item<sbyte>> SelectedDebugMcbjSetResultCodeItem { get; }

        /// <summary>
        /// Debug Port コマンド「asz set」に対する選択中の Result Code 項目を取得する。
        /// </summary>
        IReactiveProperty<Item<sbyte>> SelectedDebugAszSetResultCodeItem { get; }

        /// <summary>
        /// Debug Port コマンド「mcbj fc/targeting/pt/fc/ac/cal start」「asz eg start」で駆動される非同期処理の選択中の処理時間（ミリ秒）項目を取得する。
        /// </summary>
        IReactiveProperty<Item<int>> SelectedDebugMcbjSubcommandTimeItem { get; }

        /// <summary>
        /// Debug Port コマンド「mcbj fc/targeting/pt/fc/ac/cal start」「asz eg/hg start」で駆動される非同期処理の動作状態を取得する。
        /// </summary>
        IReadOnlyReactiveProperty<bool> DebugMcbjRunning { get; }

        /// <summary>
        /// Debug Port の受信内容を講読する。
        /// 注意: Subscribe() 時には送出しない。
        /// </summary>
        /// <param name="callback">コールバック</param>
        /// <returns>講読終了用 IDisposable オブジェクト</returns>
        /// <exception cref="ArgumentNullException">callback が null</exception>
        IDisposable DebugSubscribe(Action<string> callback);

        /// <summary>
        /// Debug Port のデータを送信する。
        /// </summary>
        /// <param name="text">送信テキスト</param>
        /// <returns>成功時 true、エラー時 false</returns>
        Task<bool> DebugTransmitAsync(string text);

        /// <summary>
        /// Debug Port の応答を挿入する。
        /// </summary>
        /// <param name="response">応答</param>
        /// <returns>A <see cref="Task"/> representing the asynchronous operation.</returns>
        Task InsertDebugResponseAsync(string response);

        /// <summary>
        /// Debug Port コマンド「mcbj fc/targeting/pt/fc/ac/cal start」「asz eg/hg start」で駆動される非同期処理を内部動作エラー要因により停止させる。
        /// </summary>
        void RaiseDebugMcbjError();
    }
}
