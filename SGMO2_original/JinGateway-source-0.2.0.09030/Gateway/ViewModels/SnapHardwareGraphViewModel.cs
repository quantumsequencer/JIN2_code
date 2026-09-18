// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.ViewModels
{
    using Sony.Jin.Gateway.Models;

    // INotifyPropertyChanged が実装されていない ViewModel はメモリリークする問題があるため、
    // ViewModel は INotifyPropertyChanged を実装すること（NotifyPropertyChangedBase は実装済み）

    /// <summary>
    /// SnapHardwareGraphViewModel
    /// </summary>
    internal class SnapHardwareGraphViewModel : HardwareGraphViewModel
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="SnapHardwareGraphViewModel"/> class.
        /// </summary>
        /// <param name="rootModel">IRootModel</param>
        /// <param name="snapHardwareGraphModel">ISnapHardwareGraphModel</param>
        public SnapHardwareGraphViewModel(IRootModel rootModel, ISnapHardwareGraphModel snapHardwareGraphModel)
            : base(rootModel, snapHardwareGraphModel, rootModel.SnapHardwareGraphVisibilityRequest)
        {
        }
    }
}
