<?php

class TestClass3 {
    public function method1(){
        $this->method2();
    }
    public function method2() {
        echo "hello world";
    }

    public function follow_both(){
        return (new TestClass1())->method2();
    }

}
