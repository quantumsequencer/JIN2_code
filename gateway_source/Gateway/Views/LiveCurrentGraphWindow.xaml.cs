// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Views
{
    using System.Windows;
    using Sony.Jin.Gateway.ViewModels;

    /// <summary>
    /// LiveCurrentGraphWindow.xaml の相互作用ロジック
    /// </summary>
    public partial class LiveCurrentGraphWindow : Window
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="LiveCurrentGraphWindow"/> class.
        /// </summary>
        /// <param name="viewModel">LiveCurrentGraphViewModel</param>
        internal LiveCurrentGraphWindow(LiveCurrentGraphViewModel viewModel)
        {
            this.DataContext = viewModel;
            this.InitializeComponent();
        }
    }
}
