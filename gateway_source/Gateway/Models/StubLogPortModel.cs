// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using System;
    using System.Reactive.Disposables;
    using System.Threading.Tasks;
    using Reactive.Bindings.Extensions;
    using Sony.Jin.Shared;

    /// <inheritdoc cref="IStubLogPortModel"/>
    internal class StubLogPortModel : DisposableBase, IStubLogPortModel
    {
        private readonly NonblockingQueue<object> queue = null;
        private readonly ILogger logger = null;
        private Action<string> logReceivedCallback = null;

        /// <summary>
        /// Initializes a new instance of the <see cref="StubLogPortModel"/> class.
        /// </summary>
        /// <param name="logger">ILogger</param>
        public StubLogPortModel(ILogger logger)
        {
            this.logger = logger;
            this.queue = new NonblockingQueue<object>().AddTo(this.CompositeDisposable);
        }

        /// <inheritdoc/>
        public IDisposable LogSubscribe(Action<string> callback)
        {
            this.logReceivedCallback += callback ?? throw new ArgumentNullException(nameof(callback));
            return Disposable.Create(() => this.logReceivedCallback -= callback);
        }

        /// <inheritdoc/>
        public Task InsertLogMessageAsync(string message)
        {
            // Log Port の Response は同時には発生しないため、順に1つずつ返すよう Queue で処理する。
            return this.queue.AddAsync(null, _ => this.InsertLogMessage(message));
        }

        private void InsertLogMessage(string message)
        {
            try
            {
                this.logReceivedCallback?.Invoke(message);
            }
            catch (Exception e)
            {
                this.logger.Exception("logReceivedCallback", $"message = {message}", e);
            }
        }
    }
}
