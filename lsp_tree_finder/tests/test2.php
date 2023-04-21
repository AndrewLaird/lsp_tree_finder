<?php

class TestClass2 {
    public function method2($message) {
        echo "This is method2 of TestClass2.";
        echo $message;
    }

    public function method3() {
        $testClass1 = new TestClass1();
        $testClass1->method2();
    }
}

