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
    /// LiveHardwareGraphViewModel
    /// </summary>
    internal class LiveHardwareGraphViewModel : HardwareGraphViewModel
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="LiveHardwareGraphViewModel"/> class.
        /// </summary>
        /// <param name="rootModel">IRootModel</param>
        /// <param name="liveHardwareGraphModel">ILiveHardwareGraphModel</param>
        /// <param name="snapHardwareGraphModel">ISnapHardwareGraphModel</param>
        public LiveHardwareGraphViewModel(IRootModel rootModel, ILiveHardwareGraphModel liveHardwareGraphModel, ISnapHardwareGraphModel snapHardwareGraphModel)
            : base(rootModel, liveHardwareGraphModel, rootModel.LiveHardwareGraphVisibilityRequest)
        {
            this.SnapCommand = new AsyncReactiveCommand<HardwareGraphSource>().WithSubscribe(x => Task.Run(() => snapHardwareGraphModel.AddGraphSource(x))).AddTo(this.CompositeDisposable);
        }

        /// <summary>
        /// スナップを取るコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand<HardwareGraphSource> SnapCommand { get; }
    }
}
