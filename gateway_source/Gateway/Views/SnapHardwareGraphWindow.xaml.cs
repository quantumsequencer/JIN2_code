// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Views
{
    using System.Windows;
    using Sony.Jin.Gateway.ViewModels;

    /// <summary>
    /// SnapHardwareGraphWindow.xaml の相互作用ロジック
    /// </summary>
    public partial class SnapHardwareGraphWindow : Window
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="SnapHardwareGraphWindow"/> class.
        /// </summary>
        /// <param name="viewModel">SnapHardwareGraphViewModel</param>
        internal SnapHardwareGraphWindow(SnapHardwareGraphViewModel viewModel)
        {
            this.DataContext = viewModel;
            this.InitializeComponent();
        }
    }
}
