// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.ViewModels
{
    using Sony.Jin.Gateway.Models;

    // INotifyPropertyChanged が実装されていない ViewModel はメモリリークする問題があるため、
    // ViewModel は INotifyPropertyChanged を実装すること（NotifyPropertyChangedBase は実装済み）

    /// <summary>
    /// SnapCurrentGraphViewModel
    /// </summary>
    internal class SnapCurrentGraphViewModel : CurrentGraphViewModel
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="SnapCurrentGraphViewModel"/> class.
        /// </summary>
        /// <param name="rootModel">IRootModel</param>
        /// <param name="snapCurrentGraphModel">ISnapCurrentGraphModel</param>
        public SnapCurrentGraphViewModel(IRootModel rootModel, ISnapCurrentGraphModel snapCurrentGraphModel)
            : base(rootModel, snapCurrentGraphModel, rootModel.SnapCurrentGraphVisibilityRequest)
        {
        }
    }
}
