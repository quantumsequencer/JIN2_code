// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using System;
    using System.Reactive.Subjects;
    using System.Runtime.CompilerServices;
    using Reactive.Bindings.Extensions;
    using Sony.Jin.Shared;

    /// <inheritdoc cref="IRootModel"/>
    internal class RootModel : DisposableBase, IRootModel
    {
        private readonly Subject<string> errorDialogRequest = null;
        private readonly Subject<bool> liveCurrentGraphVisibilityRequest = null;
        private readonly Subject<bool> snapCurrentGraphVisibilityRequest = null;
        private readonly Subject<bool> liveHardwareGraphVisibilityRequest = null;
        private readonly Subject<bool> snapHardwareGraphVisibilityRequest = null;
        private readonly Subject<bool> loopbackVisibilityRequest = null;
        private readonly Subject<bool> stubVisibilityRequest = null;
        private readonly Subject<bool> optionsVisibilityRequest = null;
        private readonly ILogger logger = null;

        /// <summary>
        /// Initializes a new instance of the <see cref="RootModel"/> class.
        /// </summary>
        /// <param name="logger">ILogger</param>
        public RootModel(ILogger logger)
        {
            this.logger = logger;
            this.errorDialogRequest = new Subject<string>().AddTo(this.CompositeDisposable);
            this.liveCurrentGraphVisibilityRequest = new Subject<bool>().AddTo(this.CompositeDisposable);
            this.snapCurrentGraphVisibilityRequest = new Subject<bool>().AddTo(this.CompositeDisposable);
            this.liveHardwareGraphVisibilityRequest = new Subject<bool>().AddTo(this.CompositeDisposable);
            this.snapHardwareGraphVisibilityRequest = new Subject<bool>().AddTo(this.CompositeDisposable);
            this.loopbackVisibilityRequest = new Subject<bool>().AddTo(this.CompositeDisposable);
            this.stubVisibilityRequest = new Subject<bool>().AddTo(this.CompositeDisposable);
            this.optionsVisibilityRequest = new Subject<bool>().AddTo(this.CompositeDisposable);
        }

        /// <inheritdoc/>
        public IObservable<string> ErrorDialogRequest => this.errorDialogRequest;

        /// <inheritdoc/>
        public IObservable<bool> LiveCurrentGraphVisibilityRequest => this.liveCurrentGraphVisibilityRequest;

        /// <inheritdoc/>
        public IObservable<bool> SnapCurrentGraphVisibilityRequest => this.snapCurrentGraphVisibilityRequest;

        /// <inheritdoc/>
        public IObservable<bool> LiveHardwareGraphVisibilityRequest => this.liveHardwareGraphVisibilityRequest;

        /// <inheritdoc/>
        public IObservable<bool> SnapHardwareGraphVisibilityRequest => this.snapHardwareGraphVisibilityRequest;

        /// <inheritdoc/>
        public IObservable<bool> LoopbackVisibilityRequest => this.loopbackVisibilityRequest;

        /// <inheritdoc/>
        public IObservable<bool> StubVisibilityRequest => this.stubVisibilityRequest;

        /// <inheritdoc/>
        public IObservable<bool> OptionsVisibilityRequest => this.optionsVisibilityRequest;

        /// <inheritdoc/>
        public void NotifyErrorDialogRequest(string message, [CallerFilePath] string callerFilePath = "", [CallerLineNumber] int callerLineNumber = -1)
        {
            this.logger.Error(message, callerFilePath, callerLineNumber);
            this.errorDialogRequest.OnNext(message);
        }

        /// <inheritdoc/>
        public void NotifyLiveCurrentGraphVisibilityRequest(bool visible)
        {
            this.liveCurrentGraphVisibilityRequest.OnNext(visible);
        }

        /// <inheritdoc/>
        public void NotifySnapCurrentGraphVisibilityRequest(bool visible)
        {
            this.snapCurrentGraphVisibilityRequest.OnNext(visible);
        }

        /// <inheritdoc/>
        public void NotifyLiveHardwareGraphVisibilityRequest(bool visible)
        {
            this.liveHardwareGraphVisibilityRequest.OnNext(visible);
        }

        /// <inheritdoc/>
        public void NotifySnapHardwareGraphVisibilityRequest(bool visible)
        {
            this.snapHardwareGraphVisibilityRequest.OnNext(visible);
        }

        /// <inheritdoc/>
        public void NotifyLoopbackVisibilityRequest(bool visible)
        {
            this.loopbackVisibilityRequest.OnNext(visible);
        }

        /// <inheritdoc/>
        public void NotifyStubVisibilityRequest(bool visible)
        {
            this.stubVisibilityRequest.OnNext(visible);
        }

        /// <inheritdoc/>
        public void NotifyOptionsVisibilityRequest(bool visible)
        {
            this.optionsVisibilityRequest.OnNext(visible);
        }
    }
}
