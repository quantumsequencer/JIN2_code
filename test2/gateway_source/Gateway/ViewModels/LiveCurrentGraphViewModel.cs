// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.ViewModels
{
    using System.Threading.Tasks;
    using Reactive.Bindings;
    using Reactive.Bindings.Extensions;
    using Sony.Jin.Gateway.Data;
    using Sony.Jin.Gateway.Models;

    // INotifyPropertyChanged が実装されていない ViewModel はメモリリークする問題があるため、
    // ViewModel は INotifyPropertyChanged を実装すること（NotifyPropertyChangedBase は実装済み）

    /// <summary>
    /// LiveCurrentGraphViewModel
    /// </summary>
    internal class LiveCurrentGraphViewModel : CurrentGraphViewModel
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="LiveCurrentGraphViewModel"/> class.
        /// </summary>
        /// <param name="rootModel">IRootModel</param>
        /// <param name="liveCurrentGraphModel">ILiveCurrentGraphModel</param>
        /// <param name="snapCurrentGraphModel">ISnapCurrentGraphModel</param>
        public LiveCurrentGraphViewModel(IRootModel rootModel, ILiveCurrentGraphModel liveCurrentGraphModel, ISnapCurrentGraphModel snapCurrentGraphModel)
            : base(rootModel, liveCurrentGraphModel, rootModel.LiveCurrentGraphVisibilityRequest)
        {
            this.SnapCommand = new AsyncReactiveCommand<CurrentGraphSource>().WithSubscribe(x => Task.Run(() => snapCurrentGraphModel.AddGraphSource(x))).AddTo(this.CompositeDisposable);
        }

        /// <summary>
        /// スナップを取るコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand<CurrentGraphSource> SnapCommand { get; }
    }
}
