// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using System;
    using System.Threading.Tasks;

    /// <summary>
    /// StubLogPortModel
    /// </summary>
    internal interface IStubLogPortModel
    {
        /// <summary>
        /// Log Port の受信内容を講読する。
        /// 注意: Subscribe() 時には送出しない。
        /// </summary>
        /// <param name="callback">コールバック</param>
        /// <returns>講読終了用 IDisposable オブジェクト</returns>
        /// <exception cref="ArgumentNullException">callback が null</exception>
        IDisposable LogSubscribe(Action<string> callback);

        /// <summary>
        /// Log Port のメッセージを挿入する。
        /// </summary>
        /// <param name="message">メッセージ</param>
        /// <returns>A <see cref="Task"/> representing the asynchronous operation.</returns>
        Task InsertLogMessageAsync(string message);
    }
}
