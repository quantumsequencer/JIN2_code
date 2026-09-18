// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Views
{
    using System.Windows;
    using Sony.Jin.Gateway.ViewModels;

    /// <summary>
    /// SnapCurrentGraphWindow.xaml の相互作用ロジック
    /// </summary>
    public partial class SnapCurrentGraphWindow : Window
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="SnapCurrentGraphWindow"/> class.
        /// </summary>
        /// <param name="viewModel">SnapCurrentGraphViewModel</param>
        internal SnapCurrentGraphWindow(SnapCurrentGraphViewModel viewModel)
        {
            this.DataContext = viewModel;
            this.InitializeComponent();
        }
    }
}
